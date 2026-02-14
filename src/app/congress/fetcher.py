"""Fetch and normalize Congressional stock trade disclosures.

Data sources (in priority order):
1. House Clerk (disclosures-clerk.house.gov) — XML index + PDF parsing
2. Senate EFD (efdsearch.senate.gov) — JSON API + HTML table parsing
3. Capitol Trades (capitoltrades.com) — fallback for either chamber
4. Local cache — last resort
"""

from __future__ import annotations

import io
import json
import logging
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx

_log = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "congress"

# Official source URLs
_HOUSE_CLERK_BASE = "https://disclosures-clerk.house.gov"
_SENATE_EFD_BASE = "https://efdsearch.senate.gov"
_CAPITOL_TRADES_URL = "https://www.capitoltrades.com/trades"

_TIMEOUT = 30.0
_DEFAULT_TTL_HOURS = 6
_RATE_LIMIT_DELAY = 0.5  # seconds between requests to gov sites


class Chamber(StrEnum):
    """Congressional chamber."""

    HOUSE = "HOUSE"
    SENATE = "SENATE"


class TransactionType(StrEnum):
    """Type of trade transaction."""

    PURCHASE = "PURCHASE"
    SALE_FULL = "SALE_FULL"
    SALE_PARTIAL = "SALE_PARTIAL"
    EXCHANGE = "EXCHANGE"


@dataclass(frozen=True, slots=True)
class CongressTrade:
    """A normalized congressional stock trade."""

    member_name: str
    chamber: str  # Chamber value
    party: str  # "D", "R", "I", or ""
    state: str  # e.g. "CA", "TX"
    ticker: str
    asset_description: str
    transaction_type: str  # TransactionType value
    trade_date: str  # YYYY-MM-DD
    filing_date: str  # YYYY-MM-DD
    amount_low: float
    amount_high: float
    owner: str  # "Self", "Spouse", "Child", "Joint", etc.
    source: str  # "house" or "senate"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _normalize_transaction_type(raw: str) -> str:
    """Map varied transaction type strings to TransactionType values."""
    lower = raw.strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
    if "purchase" in lower:
        return TransactionType.PURCHASE
    if "sale_full" in lower or "sale_full" in lower.replace("-", "_"):
        return TransactionType.SALE_FULL
    if "sale_partial" in lower or "sale_partial" in lower.replace("-", "_"):
        return TransactionType.SALE_PARTIAL
    if "sale" in lower:
        return TransactionType.SALE_PARTIAL
    if "exchange" in lower:
        return TransactionType.EXCHANGE
    return TransactionType.PURCHASE


def _parse_amount_range(amount_str: str) -> tuple[float, float]:
    """Parse amount range like '$1,001 - $15,000' into (low, high)."""
    if not amount_str or amount_str.strip() == "--":
        return (0.0, 0.0)

    numbers = re.findall(r"[\d,]+", amount_str.replace("$", ""))
    if not numbers:
        return (0.0, 0.0)

    values = [float(n.replace(",", "")) for n in numbers]
    if len(values) >= 2:
        return (values[0], values[1])
    if len(values) == 1:
        return (values[0], values[0])
    return (0.0, 0.0)


def _deduplicate_trades(trades: list[CongressTrade]) -> list[CongressTrade]:
    """Remove duplicate trades by (member, ticker, date, type)."""
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[CongressTrade] = []
    for t in trades:
        key = (t.member_name, t.ticker, t.trade_date, t.transaction_type)
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


_OWNER_CODES: dict[str, str] = {
    "SP": "Spouse",
    "JT": "Joint",
    "DC": "Dependent Child",
    "CS": "Child",
    "": "Self",
}


def _expand_owner(code: str) -> str:
    """Expand owner abbreviation code to full string."""
    return _OWNER_CODES.get(code.strip().upper(), code.strip().title() or "Self")


def _normalize_party(party_str: str) -> str:
    """Normalize party string to single letter: D, R, I, or ''."""
    lower = party_str.strip().lower()
    if lower.startswith("democrat"):
        return "D"
    if lower.startswith("republican"):
        return "R"
    if lower.startswith("independent"):
        return "I"
    upper = party_str.strip().upper()
    if upper in ("D", "R", "I"):
        return upper
    return ""


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def _is_cache_stale(source: str, ttl_hours: int = _DEFAULT_TTL_HOURS) -> bool:
    """Check if cached data for a source is stale."""
    meta_path = _CACHE_DIR / "fetch_meta.json"
    if not meta_path.exists():
        return True

    meta = json.loads(meta_path.read_text())
    last_fetch = meta.get(f"{source}_last_fetch")
    if not last_fetch:
        return True

    fetched_at = datetime.fromisoformat(last_fetch)
    return datetime.now(tz=UTC) - fetched_at > timedelta(hours=ttl_hours)


def _update_fetch_meta(source: str) -> None:
    """Update fetch timestamp for a source."""
    meta_path = _CACHE_DIR / "fetch_meta.json"
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    meta: dict[str, str] = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())

    meta[f"{source}_last_fetch"] = datetime.now(tz=UTC).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2))


def _load_cached(source: str) -> list[dict[str, Any]] | None:
    """Load cached raw data for a source."""
    cache_path = _CACHE_DIR / f"{source}_raw.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())  # type: ignore[no-any-return]
    return None


def _save_cache(source: str, data: list[dict[str, Any]]) -> None:
    """Save raw data to cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _CACHE_DIR / f"{source}_raw.json"
    cache_path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# Source 1: House Clerk (disclosures-clerk.house.gov)
# ---------------------------------------------------------------------------

def _fetch_house_xml_index(
    client: httpx.Client,
    year: int,
) -> list[dict[str, str]]:
    """Download the FD.zip for a year and parse the XML index.

    Returns list of dicts with keys: last, first, suffix, filing_type,
    state_dst, year, filing_date, doc_id.
    Only returns PTR filings (filing_type == 'P').
    """
    url = f"{_HOUSE_CLERK_BASE}/public_disc/financial-pdfs/{year}FD.zip"
    resp = client.get(url)
    resp.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    xml_name = f"{year}FD.xml"
    if xml_name not in zf.namelist():
        return []

    xml_bytes = zf.read(xml_name)
    root = ET.fromstring(xml_bytes)  # noqa: S314

    results: list[dict[str, str]] = []
    for member in root.findall("Member"):
        filing_type = (member.findtext("FilingType") or "").strip()
        if filing_type != "P":  # Only PTR filings
            continue
        results.append({
            "last": (member.findtext("Last") or "").strip(),
            "first": (member.findtext("First") or "").strip(),
            "suffix": (member.findtext("Suffix") or "").strip(),
            "filing_type": filing_type,
            "state_dst": (member.findtext("StateDst") or "").strip(),
            "year": (member.findtext("Year") or "").strip(),
            "filing_date": (member.findtext("FilingDate") or "").strip(),
            "doc_id": (member.findtext("DocID") or "").strip(),
        })

    return results


def _parse_house_ptr_pdf(
    pdf_bytes: bytes,
    member_name: str,
    state_dst: str,
    filing_date_str: str,
) -> list[dict[str, Any]]:
    """Parse a House PTR PDF and extract stock transactions.

    Uses pdfplumber to extract text, then regex to parse transaction lines.
    """
    try:
        import pdfplumber
    except ImportError:
        _log.warning("pdfplumber not installed; cannot parse House PTR PDFs")
        return []

    trades: list[dict[str, Any]] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # Parse transactions from the text.
            # {owner} {desc} ({TICKER}) [{type}] {P|S|E} {date} {amount}
            # The transaction lines follow the table header row.
            lines = text.split("\n")
            for line in lines:
                # Match lines with a ticker in parentheses and a transaction type
                tx_match = re.search(
                    r"^(\w{0,3})\s+"  # Owner code (SP, JT, DC, or empty)
                    r"(.+?)"  # Asset description
                    r"\(([A-Z]{1,5})\)"  # Ticker in parentheses
                    r"\s+\[ST\]"  # [ST] = stock type marker
                    r"\s+([PSE])\s+"  # Transaction type: P=Purchase, S=Sale, E=Exchange
                    r"(\d{2}/\d{2}/\d{4})\s+"  # Transaction date
                    r"(\d{2}/\d{2}/\d{4})\s+"  # Notification date
                    r"(.+)$",  # Amount range
                    line,
                )
                if tx_match:
                    owner_code = tx_match.group(1)
                    description = tx_match.group(2).strip()
                    ticker = tx_match.group(3)
                    tx_type_code = tx_match.group(4)
                    tx_date_raw = tx_match.group(5)
                    notif_date_raw = tx_match.group(6)
                    amount_str = tx_match.group(7).strip()

                    # Convert date from MM/DD/YYYY to YYYY-MM-DD
                    try:
                        tx_date = datetime.strptime(  # noqa: DTZ007
                            tx_date_raw, "%m/%d/%Y",
                        ).strftime("%Y-%m-%d")
                    except ValueError:
                        continue

                    try:
                        notif_date = datetime.strptime(  # noqa: DTZ007
                            notif_date_raw, "%m/%d/%Y",
                        ).strftime("%Y-%m-%d")
                    except ValueError:
                        notif_date = ""

                    low, high = _parse_amount_range(amount_str)

                    trades.append({
                        "member_name": member_name,
                        "state": state_dst[:2] if state_dst else "",
                        "ticker": ticker,
                        "asset_description": description,
                        "tx_type": tx_type_code,
                        "trade_date": tx_date,
                        "filing_date": notif_date or filing_date_str,
                        "amount_low": low,
                        "amount_high": high,
                        "owner": owner_code,
                        "source": "house",
                    })

    return trades


def _fetch_house_from_clerk(
    days: int = 120,
) -> list[CongressTrade]:
    """Fetch House trades from the official Clerk disclosure site.

    Downloads the annual XML index, filters for recent PTR filings,
    then downloads and parses each PTR PDF for stock transactions.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    current_year = datetime.now(tz=UTC).year
    years = list({current_year, cutoff.year})

    all_trades: list[CongressTrade] = []

    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
        # Collect all PTR filings from relevant years
        all_filings: list[dict[str, str]] = []
        for year in years:
            try:
                filings = _fetch_house_xml_index(client, year)
                all_filings.extend(filings)
                _log.debug("House Clerk %d: %d PTR filings", year, len(filings))
            except httpx.HTTPError as exc:
                _log.warning("House Clerk XML index %d failed: %s", year, exc)

        # Filter to recent filings only
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        recent_filings = []
        for f in all_filings:
            try:
                fd = datetime.strptime(f["filing_date"], "%m/%d/%Y")  # noqa: DTZ007
                fd_iso = fd.strftime("%Y-%m-%d")
                if fd_iso >= cutoff_str:
                    f["filing_date_iso"] = fd_iso
                    recent_filings.append(f)
            except ValueError:
                continue

        _log.info(
            "House Clerk: %d recent PTR filings to process",
            len(recent_filings),
        )

        # Download and parse each PTR PDF
        for filing in recent_filings:
            doc_id = str(filing["doc_id"])
            filing_year = str(filing["year"])
            name_parts = [filing.get("first", ""), filing.get("last", "")]
            if filing.get("suffix"):
                name_parts.append(filing["suffix"])
            member_name = " ".join(p for p in name_parts if p)
            state_dst = filing.get("state_dst", "")

            pdf_url = (
                f"{_HOUSE_CLERK_BASE}/public_disc/ptr-pdfs/{filing_year}/{doc_id}.pdf"
            )
            try:
                time.sleep(_RATE_LIMIT_DELAY)
                resp = client.get(pdf_url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                _log.debug("House PTR PDF %s failed: %s", doc_id, exc)
                continue

            raw_trades = _parse_house_ptr_pdf(
                resp.content,
                member_name=member_name,
                state_dst=state_dst,
                filing_date_str=filing.get("filing_date_iso", ""),
            )

            for raw in raw_trades:
                ticker = str(raw.get("ticker", "")).strip().upper()
                if not ticker or len(ticker) > 10:
                    continue

                tx_code = str(raw.get("tx_type", "P")).upper()
                if tx_code == "P":
                    tx_type = TransactionType.PURCHASE
                elif tx_code == "S":
                    tx_type = TransactionType.SALE_PARTIAL
                elif tx_code == "E":
                    tx_type = TransactionType.EXCHANGE
                else:
                    tx_type = TransactionType.PURCHASE

                all_trades.append(CongressTrade(
                    member_name=str(raw.get("member_name", "Unknown")),
                    chamber=Chamber.HOUSE,
                    party="",  # Not in PTR PDF
                    state=str(raw.get("state", ""))[:2].upper(),
                    ticker=ticker,
                    asset_description=str(raw.get("asset_description", "")),
                    transaction_type=tx_type,
                    trade_date=str(raw.get("trade_date", "")),
                    filing_date=str(raw.get("filing_date", "")),
                    amount_low=float(str(raw.get("amount_low", 0))),
                    amount_high=float(str(raw.get("amount_high", 0))),
                    owner=_expand_owner(str(raw.get("owner", ""))),
                    source="house",
                ))

    return all_trades


# ---------------------------------------------------------------------------
# Source 2: Senate EFD (efdsearch.senate.gov)
# ---------------------------------------------------------------------------

def _senate_efd_session(
    client: httpx.Client,
) -> str:
    """Establish a session with the Senate EFD site (CSRF + agreement).

    Returns the CSRF token for subsequent requests.
    """
    # Step 1: Get CSRF token from landing page
    resp = client.get(f"{_SENATE_EFD_BASE}/search/home/")
    resp.raise_for_status()

    csrf = resp.cookies.get("csrftoken") or resp.cookies.get("csrf") or ""
    token_match = re.search(
        r'name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']*)',
        resp.text,
    )
    form_token = token_match.group(1) if token_match else ""

    # Step 2: Accept the prohibition agreement
    client.post(
        f"{_SENATE_EFD_BASE}/search/home/",
        data={
            "prohibition_agreement": "1",
            "csrfmiddlewaretoken": form_token,
        },
        headers={
            "Referer": f"{_SENATE_EFD_BASE}/search/home/",
            "X-CSRFToken": csrf or form_token,
        },
    )

    # Updated CSRF after agreement
    return (
        client.cookies.get("csrftoken")
        or client.cookies.get("csrf")
        or csrf
        or form_token
    )


def _fetch_senate_report_list(
    client: httpx.Client,
    csrf: str,
    start_date: str = "01/01/2025 00:00:00",
    max_records: int = 200,
) -> list[dict[str, str]]:
    """Fetch list of Senate PTR filings from EFD search API.

    Returns list of dicts with: first_name, last_name, full_name,
    report_url, filing_date.
    """
    results: list[dict[str, str]] = []
    offset = 0
    batch = 100

    while offset < max_records:
        time.sleep(_RATE_LIMIT_DELAY)
        resp = client.post(
            f"{_SENATE_EFD_BASE}/search/report/data/",
            data={
                "start": str(offset),
                "length": str(batch),
                "report_types": "[11]",  # 11 = Periodic Transaction Report
                "filer_types": "[]",
                "submitted_start_date": start_date,
                "submitted_end_date": "",
                "candidate_state": "",
                "senator_state": "",
                "office_id": "",
                "first_name": "",
                "last_name": "",
                "csrfmiddlewaretoken": csrf,
            },
            headers={
                "Referer": f"{_SENATE_EFD_BASE}/search/",
                "X-CSRFToken": csrf,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("data", [])
        if not records:
            break

        for record in records:
            if len(record) < 5:
                continue
            link_match = re.search(r'href="([^"]+)"', str(record[3]))
            if link_match:
                results.append({
                    "first_name": str(record[0]).strip(),
                    "last_name": str(record[1]).strip(),
                    "full_name": str(record[2]).strip(),
                    "report_url": link_match.group(1),
                    "filing_date": str(record[4]).strip(),
                })

        if len(records) < batch:
            break
        offset += batch

    return results


def _parse_senate_report_page(
    client: httpx.Client,
    report_url: str,
    member_name: str,
    filing_date: str,
) -> list[dict[str, Any]]:
    """Parse a Senate PTR HTML page for transactions.

    The page has a <tbody> with rows containing:
    [#, date, owner, ticker, description, asset_type, tx_type, amount, comment]
    """
    time.sleep(_RATE_LIMIT_DELAY)
    full_url = f"{_SENATE_EFD_BASE}{report_url}"
    resp = client.get(full_url)
    resp.raise_for_status()

    trades: list[dict[str, Any]] = []
    html = resp.text

    # Find tbody content
    tbody_match = re.search(
        r"<tbody[^>]*>(.*?)</tbody>", html, re.DOTALL | re.IGNORECASE,
    )
    if not tbody_match:
        return trades

    tbody = tbody_match.group(1)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbody, re.DOTALL | re.IGNORECASE)

    for row in rows:
        cells = re.findall(
            r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE,
        )
        # Clean HTML tags from cells
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]

        if len(clean) < 7:
            continue

        # [#, date, owner, ticker, desc, asset_type, tx_type, amount]
        tx_date_raw = clean[1].strip()
        owner = clean[2].strip()
        ticker = clean[3].strip().replace("--", "").strip()
        description = re.sub(r"\s+", " ", clean[4]).strip()
        tx_type_raw = clean[6].strip()
        amount_str = clean[7].strip() if len(clean) > 7 else ""

        # Convert date from MM/DD/YYYY to YYYY-MM-DD
        try:
            tx_date = datetime.strptime(  # noqa: DTZ007
                tx_date_raw, "%m/%d/%Y",
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

        # Skip non-stock transactions
        if not ticker or ticker == "--":
            continue

        low, high = _parse_amount_range(amount_str)

        trades.append({
            "member_name": member_name,
            "ticker": ticker.upper(),
            "asset_description": description,
            "tx_type": tx_type_raw,
            "trade_date": tx_date,
            "filing_date": filing_date,
            "amount_low": low,
            "amount_high": high,
            "owner": owner,
            "source": "senate",
        })

    return trades


def _fetch_senate_from_efd(
    days: int = 120,
) -> list[CongressTrade]:
    """Fetch Senate trades from the official EFD search site."""
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    start_date = cutoff.strftime("%m/%d/%Y 00:00:00")

    all_trades: list[CongressTrade] = []

    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            csrf = _senate_efd_session(client)
        except httpx.HTTPError as exc:
            _log.warning("Senate EFD session setup failed: %s", exc)
            return []

        try:
            reports = _fetch_senate_report_list(
                client, csrf, start_date=start_date,
            )
            _log.info("Senate EFD: %d PTR reports found", len(reports))
        except httpx.HTTPError as exc:
            _log.warning("Senate EFD report listing failed: %s", exc)
            return []

        for report in reports:
            try:
                filing_date_raw = report.get("filing_date", "")
                try:
                    filing_date = datetime.strptime(  # noqa: DTZ007
                        filing_date_raw, "%m/%d/%Y",
                    ).strftime("%Y-%m-%d")
                except ValueError:
                    filing_date = filing_date_raw

                raw_trades = _parse_senate_report_page(
                    client,
                    report["report_url"],
                    member_name=report.get("full_name", "Unknown"),
                    filing_date=filing_date,
                )

                for raw in raw_trades:
                    ticker = str(raw.get("ticker", "")).strip().upper()
                    if not ticker or len(ticker) > 10:
                        continue

                    all_trades.append(CongressTrade(
                        member_name=str(raw.get("member_name", "Unknown")),
                        chamber=Chamber.SENATE,
                        party="",
                        state="",
                        ticker=ticker,
                        asset_description=str(
                            raw.get("asset_description", ""),
                        ),
                        transaction_type=_normalize_transaction_type(
                            str(raw.get("tx_type", "Purchase")),
                        ),
                        trade_date=str(raw.get("trade_date", "")),
                        filing_date=str(raw.get("filing_date", "")),
                        amount_low=float(str(raw.get("amount_low", 0))),
                        amount_high=float(str(raw.get("amount_high", 0))),
                        owner=str(raw.get("owner", "Self")),
                        source="senate",
                    ))

            except httpx.HTTPError as exc:
                _log.debug(
                    "Senate PTR report parse failed: %s", exc,
                )

    return all_trades


# ---------------------------------------------------------------------------
# Source 3: Capitol Trades (fallback)
# ---------------------------------------------------------------------------

def _extract_trades_from_ct_html(html: str) -> list[dict[str, Any]]:
    """Extract trade data from Capitol Trades HTML page.

    Capitol Trades uses Next.js RSC streaming. Trade data is embedded
    in self.__next_f.push() calls as escaped JSON within a "data" array.
    """
    pushes = re.findall(
        r'self\.__next_f\.push\(\[1,"(.+?)"\]\)', html, re.DOTALL,
    )

    for chunk in pushes:
        unescaped = chunk.replace('\\"', '"').replace("\\/", "/")
        data_match = re.search(
            r'"data":\s*(\[\{.*?\}(?:,\{.*?\})*\])', unescaped, re.DOTALL,
        )
        if data_match:
            try:
                data_str = data_match.group(1)
                trades = json.loads(data_str)
                if (
                    trades
                    and isinstance(trades, list)
                    and isinstance(trades[0], dict)
                    and "txDate" in trades[0]
                ):
                    return trades  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                continue

    return []


def _clean_ticker(raw_ticker: str) -> str:
    """Clean Capitol Trades ticker format (e.g. 'HWM:US' -> 'HWM')."""
    if not raw_ticker:
        return ""
    ticker = raw_ticker.split(":")[0]
    ticker = ticker.lstrip("$")
    return ticker.strip().upper()


def _normalize_capitol_trade(raw: dict[str, Any]) -> CongressTrade | None:
    """Normalize a Capitol Trades record to CongressTrade."""
    issuer = raw.get("issuer") or {}
    if not isinstance(issuer, dict):
        return None

    raw_ticker = str(issuer.get("issuerTicker", ""))
    ticker = _clean_ticker(raw_ticker)
    if not ticker or len(ticker) > 10:
        return None

    trade_date = str(raw.get("txDate", "")).strip()
    if not trade_date:
        return None

    politician = raw.get("politician") or {}
    if not isinstance(politician, dict):
        return None

    first = str(politician.get("firstName", ""))
    last = str(politician.get("lastName", ""))
    name = f"{first} {last}".strip() or "Unknown"

    chamber_raw = str(raw.get("chamber", "")).lower()
    chamber = Chamber.HOUSE if chamber_raw == "house" else Chamber.SENATE

    party = _normalize_party(str(politician.get("party", "")))
    state = str(politician.get("_stateId", "")).upper()

    tx_type = str(raw.get("txType", "")).lower()
    if tx_type == "buy":
        transaction_type = TransactionType.PURCHASE
    elif tx_type == "sell":
        transaction_type = TransactionType.SALE_PARTIAL
    elif tx_type == "sell_full":
        transaction_type = TransactionType.SALE_FULL
    elif tx_type == "exchange":
        transaction_type = TransactionType.EXCHANGE
    else:
        transaction_type = TransactionType.PURCHASE

    value = float(str(raw.get("value", 0) or 0))
    pub_date = str(raw.get("pubDate", ""))
    filing_date = pub_date[:10] if len(pub_date) >= 10 else ""
    owner_raw = str(raw.get("owner", "self")).replace("-", " ").title()

    return CongressTrade(
        member_name=name,
        chamber=chamber,
        party=party,
        state=state,
        ticker=ticker,
        asset_description=str(issuer.get("issuerName", "")),
        transaction_type=transaction_type,
        trade_date=trade_date,
        filing_date=filing_date,
        amount_low=value * 0.5 if value else 0.0,
        amount_high=value * 1.5 if value else 0.0,
        owner=owner_raw,
        source=chamber_raw,
    )


def _fetch_from_capitol_trades(
    max_pages: int = 5,
) -> list[CongressTrade]:
    """Fetch trades from Capitol Trades (both chambers)."""
    all_trades: list[CongressTrade] = []

    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            resp = client.get(
                _CAPITOL_TRADES_URL,
                params={"page": page, "pageSize": 100},
            )
            resp.raise_for_status()
            raw_trades = _extract_trades_from_ct_html(resp.text)
            if not raw_trades:
                break
            for raw in raw_trades:
                t = _normalize_capitol_trade(raw)
                if t is not None:
                    all_trades.append(t)

    return all_trades


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_house_trades(
    *,
    force_refresh: bool = False,
    ttl_hours: int = _DEFAULT_TTL_HOURS,
) -> list[CongressTrade]:
    """Fetch House trades. Callers should prefer fetch_all_trades()."""
    if not force_refresh and not _is_cache_stale("house_clerk", ttl_hours):
        cached = _load_cached("house_clerk")
        if cached is not None:
            return [
                t for raw in cached
                if (t := _normalize_capitol_trade(raw)) is not None
            ]
    return []


def fetch_senate_trades(
    *,
    force_refresh: bool = False,
    ttl_hours: int = _DEFAULT_TTL_HOURS,
) -> list[CongressTrade]:
    """Fetch Senate trades. Callers should prefer fetch_all_trades()."""
    if not force_refresh and not _is_cache_stale("senate_efd", ttl_hours):
        cached = _load_cached("senate_efd")
        if cached is not None:
            return [
                t for raw in cached
                if (t := _normalize_capitol_trade(raw)) is not None
            ]
    return []


def _deserialize_cached_trades(
    cached: list[dict[str, Any]],
) -> list[CongressTrade]:
    """Deserialize cached trade dicts back to CongressTrade objects.

    Handles both CongressTrade-serialized dicts (from official sources)
    and Capitol Trades format dicts.
    """
    trades: list[CongressTrade] = []
    for raw in cached:
        # Try as a serialized CongressTrade dict first
        if "member_name" in raw and "ticker" in raw:
            try:
                t = CongressTrade(
                    member_name=str(raw.get("member_name", "")),
                    chamber=str(raw.get("chamber", "HOUSE")),
                    party=str(raw.get("party", "")),
                    state=str(raw.get("state", "")),
                    ticker=str(raw.get("ticker", "")),
                    asset_description=str(raw.get("asset_description", "")),
                    transaction_type=str(raw.get("transaction_type", "")),
                    trade_date=str(raw.get("trade_date", "")),
                    filing_date=str(raw.get("filing_date", "")),
                    amount_low=float(str(raw.get("amount_low", 0))),
                    amount_high=float(str(raw.get("amount_high", 0))),
                    owner=str(raw.get("owner", "")),
                    source=str(raw.get("source", "")),
                )
                trades.append(t)
                continue
            except (TypeError, KeyError, ValueError):
                pass
        # Fall back to Capitol Trades normalizer
        ct = _normalize_capitol_trade(raw)
        if ct is not None:
            trades.append(ct)
    return trades


def fetch_all_trades(
    days: int = 90,
    *,
    force_refresh: bool = False,
) -> list[CongressTrade]:
    """Fetch and merge trades from both chambers, filtered by recency.

    Data source priority:
    1. Official: House Clerk + Senate EFD (parallel)
    2. Fallback: Capitol Trades (both chambers)
    3. Cache: local cache from previous successful fetches
    """
    trades: list[CongressTrade] = []

    # Check combined cache first
    if not force_refresh and not _is_cache_stale("official"):
        cached = _load_cached("official")
        if cached is not None:
            trades = _deserialize_cached_trades(cached)
            if trades:
                _log.debug("Loaded %d trades from official cache", len(trades))

    # Try official sources
    if not trades:
        house_trades: list[CongressTrade] = []
        senate_trades: list[CongressTrade] = []

        # House Clerk
        try:
            house_trades = _fetch_house_from_clerk(days=days + 30)
            _log.info(
                "House Clerk: fetched %d trades", len(house_trades),
            )
        except Exception as exc:
            _log.warning("House Clerk fetch failed: %s", exc)

        # Senate EFD
        try:
            senate_trades = _fetch_senate_from_efd(days=days + 30)
            _log.info(
                "Senate EFD: fetched %d trades", len(senate_trades),
            )
        except Exception as exc:
            _log.warning("Senate EFD fetch failed: %s", exc)

        trades = house_trades + senate_trades

        if trades:
            # Cache as serialized dicts
            cache_data: list[dict[str, Any]] = [
                asdict(t) for t in trades
            ]
            _save_cache("official", cache_data)
            _update_fetch_meta("official")

    # Fallback to Capitol Trades if official sources returned nothing
    if not trades:
        _log.info("Official sources empty; falling back to Capitol Trades")
        try:
            trades = _fetch_from_capitol_trades()
            if trades:
                cache_data = [asdict(t) for t in trades]
                _save_cache("capitol_trades", cache_data)
                _update_fetch_meta("capitol_trades")
                _log.info(
                    "Capitol Trades fallback: %d trades", len(trades),
                )
            else:
                _log.warning("Capitol Trades returned no data")
        except httpx.HTTPError as exc:
            _log.warning("Capitol Trades fallback failed: %s", exc)

    # Final fallback: any available cache
    if not trades:
        for cache_name in ("official", "capitol_trades"):
            cached = _load_cached(cache_name)
            if cached:
                _log.info("Using cached %s data", cache_name)
                trades = _deserialize_cached_trades(cached)
                if trades:
                    break

    if not trades:
        _log.warning("No Congress trade data available from any source")
        print(  # noqa: T201
            "WARNING: No Congress trade data available. "
            "Check network connectivity to gov sites.",
            file=sys.stderr,
        )

    all_trades = _deduplicate_trades(trades)

    # Filter by date window
    cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [t for t in all_trades if t.trade_date >= cutoff]

    # Sort by trade date descending
    return sorted(recent, key=lambda t: t.trade_date, reverse=True)


def trade_to_dict(trade: CongressTrade) -> dict[str, object]:
    """Convert a trade to a serializable dict."""
    return asdict(trade)

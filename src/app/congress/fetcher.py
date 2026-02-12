"""Fetch and normalize Congressional stock trade disclosures."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

import httpx

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "congress"

_HOUSE_URL = (
    "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com"
    "/data/all_transactions.json"
)
_SENATE_URL = (
    "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com"
    "/aggregate/all_transactions.json"
)

_TIMEOUT = 30.0
_DEFAULT_TTL_HOURS = 6


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
        # Generic sale defaults to partial
        return TransactionType.SALE_PARTIAL
    if "exchange" in lower:
        return TransactionType.EXCHANGE
    return TransactionType.PURCHASE  # default


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


def _load_cached(source: str) -> list[dict[str, object]] | None:
    """Load cached raw data for a source."""
    cache_path = _CACHE_DIR / f"{source}_raw.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())  # type: ignore[no-any-return]
    return None


def _save_cache(source: str, data: list[dict[str, object]]) -> None:
    """Save raw data to cache."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _CACHE_DIR / f"{source}_raw.json"
    cache_path.write_text(json.dumps(data))


def _normalize_house_trade(raw: dict[str, object]) -> CongressTrade | None:
    """Normalize a single House trade record."""
    ticker = str(raw.get("ticker", "")).strip().upper()
    if not ticker or ticker == "--" or len(ticker) > 10:
        return None

    trade_date = str(raw.get("transaction_date", "")).strip()
    if not trade_date:
        return None

    amount_str = str(raw.get("amount", ""))
    low, high = _parse_amount_range(amount_str)

    return CongressTrade(
        member_name=str(raw.get("representative", "Unknown")),
        chamber=Chamber.HOUSE,
        party=str(raw.get("party", "")),
        state=str(raw.get("state", "")),
        ticker=ticker,
        asset_description=str(raw.get("asset_description", "")),
        transaction_type=_normalize_transaction_type(
            str(raw.get("type", "purchase")),
        ),
        trade_date=trade_date,
        filing_date=str(raw.get("disclosure_date", "")),
        amount_low=low,
        amount_high=high,
        owner=str(raw.get("owner", "Self")),
        source="house",
    )


def _normalize_senate_trade(raw: dict[str, object]) -> CongressTrade | None:
    """Normalize a single Senate trade record."""
    ticker = str(raw.get("ticker", "")).strip().upper()
    if not ticker or ticker == "--" or len(ticker) > 10:
        return None

    trade_date = str(raw.get("transaction_date", "")).strip()
    if not trade_date:
        return None

    amount_str = str(raw.get("amount", ""))
    low, high = _parse_amount_range(amount_str)

    # Senate data has senator name + party/state in separate fields
    name = str(raw.get("senator", "") or raw.get("full_name", "Unknown"))
    party = str(raw.get("party", ""))
    state = str(raw.get("state", ""))

    return CongressTrade(
        member_name=name,
        chamber=Chamber.SENATE,
        party=party,
        state=state,
        ticker=ticker,
        asset_description=str(raw.get("asset_description", "")),
        transaction_type=_normalize_transaction_type(
            str(raw.get("type", "purchase")),
        ),
        trade_date=trade_date,
        filing_date=str(raw.get("disclosure_date", "")),
        amount_low=low,
        amount_high=high,
        owner=str(raw.get("owner", "Self")),
        source="senate",
    )


def fetch_house_trades(
    *,
    force_refresh: bool = False,
    ttl_hours: int = _DEFAULT_TTL_HOURS,
) -> list[CongressTrade]:
    """Fetch House trades from S3 (cached)."""
    if not force_refresh and not _is_cache_stale("house", ttl_hours):
        cached = _load_cached("house")
        if cached is not None:
            trades = []
            for raw in cached:
                t = _normalize_house_trade(raw)
                if t is not None:
                    trades.append(t)
            return trades

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(_HOUSE_URL)
            resp.raise_for_status()
            raw_data: list[dict[str, object]] = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        # Fall back to cache if available
        cached = _load_cached("house")
        if cached is not None:
            raw_data = cached
        else:
            return []

    _save_cache("house", raw_data)
    _update_fetch_meta("house")

    trades = []
    for raw in raw_data:
        t = _normalize_house_trade(raw)
        if t is not None:
            trades.append(t)
    return trades


def fetch_senate_trades(
    *,
    force_refresh: bool = False,
    ttl_hours: int = _DEFAULT_TTL_HOURS,
) -> list[CongressTrade]:
    """Fetch Senate trades from S3 (cached)."""
    if not force_refresh and not _is_cache_stale("senate", ttl_hours):
        cached = _load_cached("senate")
        if cached is not None:
            trades = []
            for raw in cached:
                t = _normalize_senate_trade(raw)
                if t is not None:
                    trades.append(t)
            return trades

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(_SENATE_URL)
            resp.raise_for_status()
            raw_data: list[dict[str, object]] = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        cached = _load_cached("senate")
        if cached is not None:
            raw_data = cached
        else:
            return []

    _save_cache("senate", raw_data)
    _update_fetch_meta("senate")

    trades = []
    for raw in raw_data:
        t = _normalize_senate_trade(raw)
        if t is not None:
            trades.append(t)
    return trades


def fetch_all_trades(
    days: int = 90,
    *,
    force_refresh: bool = False,
) -> list[CongressTrade]:
    """Fetch and merge trades from both chambers, filtered by recency."""
    house = fetch_house_trades(force_refresh=force_refresh)
    senate = fetch_senate_trades(force_refresh=force_refresh)

    all_trades = _deduplicate_trades(house + senate)

    # Filter by date window
    cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [t for t in all_trades if t.trade_date >= cutoff]

    # Sort by trade date descending
    return sorted(recent, key=lambda t: t.trade_date, reverse=True)


def trade_to_dict(trade: CongressTrade) -> dict[str, object]:
    """Convert a trade to a serializable dict."""
    return asdict(trade)

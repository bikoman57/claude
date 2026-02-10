from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

_EDGAR_BASE = "https://data.sec.gov/submissions"


@dataclass(frozen=True, slots=True)
class Filing:
    """A SEC filing for a company."""

    ticker: str
    company_name: str
    form_type: str
    filed_date: str
    description: str
    url: str
    materiality: str  # HIGH / MEDIUM / LOW


def classify_materiality(
    form_type: str,
    description: str = "",
) -> str:
    """Classify filing materiality."""
    if form_type in ("10-K", "10-K/A"):
        return "HIGH"
    if form_type in ("10-Q", "10-Q/A"):
        return "MEDIUM"
    desc_lower = description.lower()
    high_keywords = [
        "earnings",
        "acquisition",
        "merger",
        "restatement",
        "bankruptcy",
        "guidance",
    ]
    if any(kw in desc_lower for kw in high_keywords):
        return "HIGH"
    if form_type.startswith("8-K"):
        return "MEDIUM"
    return "LOW"


def fetch_recent_filings(
    cik: str,
    ticker: str,
    email: str,
    form_types: tuple[str, ...] = ("10-K", "10-Q", "8-K"),
    days: int = 30,
) -> list[Filing]:
    """Fetch recent filings from SEC EDGAR for one company."""
    url = f"{_EDGAR_BASE}/CIK{cik}.json"
    headers = {"User-Agent": f"fin-agents {email}"}

    with httpx.Client() as client:
        resp = client.get(url, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

    company_name = data.get("name", ticker)
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    descriptions = recent.get("primaryDocDescription", [])
    accessions = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])

    cutoff = (
        datetime.now(tz=UTC) - timedelta(days=days)
    ).strftime("%Y-%m-%d")

    filings: list[Filing] = []
    for i, form in enumerate(forms):
        if form not in form_types:
            continue
        filed_date = dates[i] if i < len(dates) else ""
        if filed_date < cutoff:
            continue
        desc = descriptions[i] if i < len(descriptions) else ""
        accession = accessions[i] if i < len(accessions) else ""
        doc = docs[i] if i < len(docs) else ""
        acc_nodash = accession.replace("-", "")
        cik_raw = cik.lstrip("0") or "0"
        filing_url = (
            "https://www.sec.gov/Archives/edgar/data"
            f"/{cik_raw}/{acc_nodash}/{doc}"
        )
        filings.append(
            Filing(
                ticker=ticker,
                company_name=company_name,
                form_type=form,
                filed_date=filed_date,
                description=desc,
                url=filing_url,
                materiality=classify_materiality(form, desc),
            ),
        )

    return filings

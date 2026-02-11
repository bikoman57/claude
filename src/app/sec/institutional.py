from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

_EDGAR_BASE = "https://data.sec.gov/submissions"


@dataclass(frozen=True, slots=True)
class InstitutionalFiler:
    """A tracked institutional investor."""

    name: str
    cik: str


@dataclass(frozen=True, slots=True)
class InstitutionalFiling:
    """A 13F filing from an institutional investor."""

    filer_name: str
    form_type: str
    filed_date: str
    url: str


TRACKED_FILERS = [
    InstitutionalFiler("Berkshire Hathaway", "0001067983"),
    InstitutionalFiler("ARK Invest", "0001803994"),
    InstitutionalFiler("BlackRock", "0001364742"),
    InstitutionalFiler("Bridgewater Associates", "0001350694"),
    InstitutionalFiler("Vanguard Group", "0000102909"),
]


def fetch_institutional_filings(
    email: str,
    days: int = 90,
) -> list[InstitutionalFiling]:
    """Fetch recent 13F filings from tracked institutions."""
    cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    headers = {"User-Agent": f"fin-agents {email}"}
    filings: list[InstitutionalFiling] = []

    for filer in TRACKED_FILERS:
        url = f"{_EDGAR_BASE}/CIK{filer.cik}.json"
        with httpx.Client() as client:
            resp = client.get(
                url,
                headers=headers,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if not form.startswith("13F"):
                continue
            filed_date = dates[i] if i < len(dates) else ""
            if filed_date < cutoff:
                continue
            accession = accessions[i] if i < len(accessions) else ""
            doc = docs[i] if i < len(docs) else ""
            acc_nodash = accession.replace("-", "")
            cik_raw = filer.cik.lstrip("0") or "0"
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik_raw}/{acc_nodash}/{doc}"
            )
            filings.append(
                InstitutionalFiling(
                    filer_name=filer.name,
                    form_type=form,
                    filed_date=filed_date,
                    url=filing_url,
                ),
            )

        time.sleep(0.1)  # EDGAR rate limit: 10 req/sec

    return filings

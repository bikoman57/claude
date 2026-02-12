from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict

from dotenv import load_dotenv

from app.sec.filings import fetch_recent_filings
from app.sec.holdings import (
    get_all_unique_holdings,
    get_holding_by_ticker,
)
from app.sec.institutional import fetch_institutional_filings

USAGE = """\
Usage:
  uv run python -m app.sec filings <ticker>   Recent SEC filings
  uv run python -m app.sec institutional      Recent 13F filings
  uv run python -m app.sec recent             All index holdings filings
"""


def _get_email() -> str:
    return os.environ.get("SEC_EDGAR_EMAIL", "")


def cmd_filings(ticker: str) -> int:
    """Fetch recent filings for one stock."""
    email = _get_email()
    if not email:
        print(  # noqa: T201
            "SEC_EDGAR_EMAIL not set.",
            file=sys.stderr,
        )
        return 1
    holding = get_holding_by_ticker(ticker.upper())
    if holding is None:
        print(  # noqa: T201
            f"Unknown ticker: {ticker}",
            file=sys.stderr,
        )
        return 1
    filings = fetch_recent_filings(
        cik=holding.cik,
        ticker=holding.ticker,
        email=email,
    )
    print(  # noqa: T201
        json.dumps([asdict(f) for f in filings], indent=2),
    )
    return 0


def cmd_institutional() -> int:
    """Fetch recent 13F filings from tracked institutions."""
    email = _get_email()
    if not email:
        print(  # noqa: T201
            "SEC_EDGAR_EMAIL not set.",
            file=sys.stderr,
        )
        return 1
    filings = fetch_institutional_filings(email)
    if not filings:
        print("No recent 13F filings found.")  # noqa: T201
        return 0
    for f in filings:
        print(  # noqa: T201
            f"  {f.filer_name}: {f.form_type} filed {f.filed_date}",
        )
    return 0


def cmd_recent() -> int:
    """Fetch filings for all unique index holdings."""
    email = _get_email()
    if not email:
        print(  # noqa: T201
            "SEC_EDGAR_EMAIL not set.",
            file=sys.stderr,
        )
        return 1
    holdings = get_all_unique_holdings()
    all_filings = []
    for h in holdings:
        try:
            filings = fetch_recent_filings(
                cik=h.cik,
                ticker=h.ticker,
                email=email,
            )
            all_filings.extend(filings)
        except Exception:  # noqa: S110
            pass
        time.sleep(0.1)  # EDGAR rate limit

    if not all_filings:
        print("No recent filings found.")  # noqa: T201
        return 0
    all_filings.sort(
        key=lambda f: f.filed_date,
        reverse=True,
    )
    for f in all_filings[:20]:
        print(  # noqa: T201
            f"  [{f.materiality}] {f.ticker} {f.form_type} {f.filed_date}",
        )
    return 0


def main() -> None:
    load_dotenv()
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]

    match command:
        case "filings" if len(sys.argv) >= 3:
            exit_code = cmd_filings(sys.argv[2])
        case "institutional":
            exit_code = cmd_institutional()
        case "recent":
            exit_code = cmd_recent()
        case _:
            print(  # noqa: T201
                f"Unknown command: {command}",
                file=sys.stderr,
            )
            print(USAGE, file=sys.stderr)  # noqa: T201
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

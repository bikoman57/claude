from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict

from dotenv import load_dotenv

from app.sec.earnings import (
    classify_earnings_proximity,
    classify_track_record,
    compute_avg_surprise,
    fetch_all_earnings_calendars,
    fetch_earnings_calendar,
)
from app.sec.filings import fetch_recent_filings
from app.sec.holdings import (
    get_all_unique_holdings,
    get_holding_by_ticker,
)
from app.sec.institutional import fetch_institutional_filings

USAGE = """\
Usage:
  uv run python -m app.sec filings <ticker>      Recent SEC filings
  uv run python -m app.sec institutional         Recent 13F filings
  uv run python -m app.sec recent                All index holdings filings
  uv run python -m app.sec earnings <ticker>     Earnings calendar and history
  uv run python -m app.sec earnings-calendar     Upcoming earnings for all holdings
  uv run python -m app.sec earnings-summary      Recent earnings beats/misses
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


def cmd_earnings(ticker: str) -> int:
    """Show earnings calendar and history for one stock."""
    holding = get_holding_by_ticker(ticker.upper())
    if holding is None:
        print(  # noqa: T201
            f"Unknown ticker: {ticker}",
            file=sys.stderr,
        )
        return 1
    try:
        cal = fetch_earnings_calendar(holding.ticker)
        print(  # noqa: T201
            json.dumps(asdict(cal), indent=2, default=str),
        )
        return 0
    except Exception as e:
        print(  # noqa: T201
            f"Error fetching earnings: {e}",
            file=sys.stderr,
        )
        return 1


def cmd_earnings_calendar() -> int:
    """Show upcoming earnings for all index holdings."""
    holdings = get_all_unique_holdings()
    calendars = fetch_all_earnings_calendars(holdings)

    upcoming = [
        c
        for c in calendars
        if c.days_until_earnings is not None and 0 < c.days_until_earnings <= 30
    ]
    upcoming.sort(key=lambda c: c.days_until_earnings or 9999)

    if not upcoming:
        print("No upcoming earnings in next 30 days.")  # noqa: T201
        return 0

    print("Upcoming earnings (next 30 days):")  # noqa: T201
    for cal in upcoming:
        proximity = classify_earnings_proximity(cal.days_until_earnings)
        print(  # noqa: T201
            f"  [{proximity:>8s}] {cal.ticker}: "
            f"{cal.next_earnings_date} ({cal.days_until_earnings}d)",
        )
    return 0


def cmd_earnings_summary() -> int:
    """Show recent earnings beats/misses for all holdings."""
    holdings = get_all_unique_holdings()
    calendars = fetch_all_earnings_calendars(holdings)

    print("Earnings track records:")  # noqa: T201
    for cal in calendars:
        if not cal.recent_events:
            continue
        track = classify_track_record(cal.recent_events)
        avg = compute_avg_surprise(cal.recent_events)
        avg_str = f"{avg:+.1%}" if avg is not None else "N/A"
        print(  # noqa: T201
            f"  {cal.ticker:>5s}: {track:<20s} (avg surprise: {avg_str})",
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
        case "earnings" if len(sys.argv) >= 3:
            exit_code = cmd_earnings(sys.argv[2])
        case "earnings-calendar":
            exit_code = cmd_earnings_calendar()
        case "earnings-summary":
            exit_code = cmd_earnings_summary()
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

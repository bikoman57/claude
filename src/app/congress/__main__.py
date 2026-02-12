"""Congress trading CLI: track Congressional stock disclosures."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime

from app.congress.fetcher import fetch_all_trades, trade_to_dict
from app.congress.members import rate_all_members
from app.congress.sectors import (
    aggregate_sectors,
    compute_overall_sentiment,
)

USAGE = """\
Usage:
  uv run python -m app.congress trades              Recent Congress trades
  uv run python -m app.congress trades --ticker AAPL Filter by ticker
  uv run python -m app.congress trades --member Pelosi Filter by member name
  uv run python -m app.congress trades --days 30     Filter by recency (default: 90)
  uv run python -m app.congress members             Member performance ratings
  uv run python -m app.congress sectors             Sector aggregation mapped to ETFs
  uv run python -m app.congress summary             Full summary for chief-analyst
"""


def _parse_arg(args: list[str], flag: str) -> str | None:
    """Parse a --flag value from argv."""
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args):
            return args[i + 1]
    return None


def cmd_trades() -> int:
    """Print recent Congressional trades as JSON."""
    args = sys.argv[2:]
    days = int(_parse_arg(args, "--days") or "90")
    ticker_filter = _parse_arg(args, "--ticker")
    member_filter = _parse_arg(args, "--member")

    trades = fetch_all_trades(days=days)

    if ticker_filter:
        ticker_upper = ticker_filter.upper()
        trades = [t for t in trades if t.ticker == ticker_upper]

    if member_filter:
        member_lower = member_filter.lower()
        trades = [t for t in trades if member_lower in t.member_name.lower()]

    output = {
        "total": len(trades),
        "days": days,
        "filters": {
            "ticker": ticker_filter,
            "member": member_filter,
        },
        "trades": [trade_to_dict(t) for t in trades[:100]],
        "as_of": datetime.now(tz=UTC).isoformat(),
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def cmd_members() -> int:
    """Print member performance ratings as JSON."""
    trades = fetch_all_trades(days=365)
    ratings = rate_all_members(trades)

    output = {
        "total_members": len(ratings),
        "members": [asdict(r) for r in ratings[:50]],
        "as_of": datetime.now(tz=UTC).isoformat(),
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def cmd_sectors() -> int:
    """Print sector aggregation mapped to ETF universe."""
    trades = fetch_all_trades(days=90)
    ratings = rate_all_members(trades)
    sectors = aggregate_sectors(trades, ratings)

    output = {
        "sectors": [asdict(s) for s in sectors],
        "overall_sentiment": compute_overall_sentiment(sectors),
        "as_of": datetime.now(tz=UTC).isoformat(),
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def cmd_summary() -> int:
    """Print full summary combining trades, members, and sectors."""
    trades_90d = fetch_all_trades(days=90)
    trades_365d = fetch_all_trades(days=365)
    ratings = rate_all_members(trades_365d)
    sectors = aggregate_sectors(trades_90d, ratings)
    overall = compute_overall_sentiment(sectors)

    # Count last 30 days
    cutoff_30d = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    from datetime import timedelta

    cutoff_30d = (datetime.now(tz=UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    trades_30d = [t for t in trades_90d if t.trade_date >= cutoff_30d]

    # Top-rated members (A and B tier)
    top = [r for r in ratings if r.tier in ("A", "B")]

    output: dict[str, object] = {
        "total_trades_90d": len(trades_90d),
        "trades_last_30d": len(trades_30d),
        "net_buying_usd": sum(s.net_buying_usd for s in sectors),
        "overall_sentiment": overall,
        "sectors": [
            {
                "sector": s.sector,
                "underlying": s.underlying_ticker,
                "leveraged": s.leveraged_ticker,
                "sentiment": s.sentiment,
                "net_usd": s.net_buying_usd,
                "trades": s.trade_count,
            }
            for s in sectors
        ],
        "top_members": [
            {
                "name": r.name,
                "tier": r.tier,
                "win_rate": r.win_rate,
                "trades": r.total_trades,
                "chamber": r.chamber,
            }
            for r in top[:10]
        ],
        "as_of": datetime.now(tz=UTC).isoformat(),
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]
    match command:
        case "trades":
            exit_code = cmd_trades()
        case "members":
            exit_code = cmd_members()
        case "sectors":
            exit_code = cmd_sectors()
        case "summary":
            exit_code = cmd_summary()
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

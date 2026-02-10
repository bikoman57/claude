from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

from app.macro.fed import build_fed_summary, get_upcoming_fomc
from app.macro.indicators import (
    fetch_dashboard,
    fetch_fred_history,
    fetch_fred_latest,
)
from app.macro.yields import fetch_yield_curve

USAGE = """\
Usage:
  uv run python -m app.macro dashboard     Full macro dashboard
  uv run python -m app.macro rates         Fed rates + trajectory
  uv run python -m app.macro yields        Treasury yield curve
  uv run python -m app.macro calendar      Upcoming FOMC dates
"""


def cmd_dashboard() -> int:
    """Print macro dashboard."""
    dashboard = fetch_dashboard()
    print(  # noqa: T201
        json.dumps(asdict(dashboard), indent=2),
    )
    return 0


def cmd_rates() -> int:
    """Print Fed rates and trajectory."""
    fred_key = os.environ.get("FRED_API_KEY", "")
    if not fred_key:
        print(  # noqa: T201
            "FRED_API_KEY not set."
            " Set it for Fed rate data.",
            file=sys.stderr,
        )
        return 1
    rate = fetch_fred_latest("FEDFUNDS", fred_key)
    history = fetch_fred_history("FEDFUNDS", fred_key, limit=6)
    summary = build_fed_summary(rate, history)
    print(json.dumps(asdict(summary), indent=2))  # noqa: T201
    return 0


def cmd_yields() -> int:
    """Print Treasury yield curve."""
    curve = fetch_yield_curve()
    print(json.dumps(asdict(curve), indent=2))  # noqa: T201
    return 0


def cmd_calendar() -> int:
    """Print upcoming FOMC dates."""
    dates = get_upcoming_fomc(count=6)
    if not dates:
        print(  # noqa: T201
            "No upcoming FOMC dates in calendar.",
        )
        return 0
    for d in dates:
        print(f"  {d.isoformat()}")  # noqa: T201
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]

    match command:
        case "dashboard":
            exit_code = cmd_dashboard()
        case "rates":
            exit_code = cmd_rates()
        case "yields":
            exit_code = cmd_yields()
        case "calendar":
            exit_code = cmd_calendar()
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

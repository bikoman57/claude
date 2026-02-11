from __future__ import annotations

import json
import sys

from app.geopolitical.classifier import (
    build_geopolitical_summary,
    classify_event,
)
from app.geopolitical.gdelt import fetch_all_gdelt_events
from app.geopolitical.rss import fetch_all_geopolitical_feeds

USAGE = """\
Usage:
  uv run python -m app.geopolitical events      GDELT events by theme
  uv run python -m app.geopolitical headlines    Geopolitical RSS headlines
  uv run python -m app.geopolitical summary      Risk summary with sector impact
"""


def cmd_events() -> int:
    """Print GDELT events."""
    events = fetch_all_gdelt_events()
    classified = [
        classify_event(
            title=e.title,
            url=e.url,
            theme=e.theme,
            tone=e.tone,
            volume=e.volume,
            date=e.date,
        )
        for e in events
    ]
    for ce in classified[:20]:
        sectors = ", ".join(ce.affected_sectors)
        print(  # noqa: T201
            f"[{ce.impact:<6}] [{ce.category}] [{sectors}] {ce.title}",
        )
    return 0


def cmd_headlines() -> int:
    """Print geopolitical RSS headlines."""
    articles = fetch_all_geopolitical_feeds()
    for a in articles[:20]:
        print(f"[{a.source}] {a.title}")  # noqa: T201
    return 0


def cmd_summary() -> int:
    """Print geopolitical risk summary as JSON."""
    events = fetch_all_gdelt_events()
    classified = [
        classify_event(
            title=e.title,
            url=e.url,
            theme=e.theme,
            tone=e.tone,
            volume=e.volume,
            date=e.date,
        )
        for e in events
    ]
    summary = build_geopolitical_summary(classified)

    output = {
        "risk_level": summary.risk_level,
        "high_impact_count": summary.high_impact_count,
        "total_events": summary.total_events,
        "events_by_category": summary.events_by_category,
        "affected_sectors": summary.affected_sectors,
        "top_events": [
            {
                "title": e.title,
                "category": e.category,
                "impact": e.impact,
                "sectors": list(e.affected_sectors),
                "tone": e.tone,
            }
            for e in summary.top_events
        ],
        "as_of": summary.as_of,
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]
    match command:
        case "events":
            exit_code = cmd_events()
        case "headlines":
            exit_code = cmd_headlines()
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

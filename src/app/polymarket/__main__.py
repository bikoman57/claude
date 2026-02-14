"""Polymarket prediction markets CLI: crowd-sourced probability signals."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

from app.polymarket.classifier import (
    TRACKED_QUERIES,
    ClassifiedMarket,
    build_prediction_summary,
    classify_market,
)
from app.polymarket.fetcher import (
    PolymarketMarket,
    _match_keywords,
    fetch_relevant_markets,
)

USAGE = """\
Usage:
  uv run python -m app.polymarket markets   Markets with probabilities
  uv run python -m app.polymarket summary   Prediction summary (JSON)
"""


def _classify_all(markets: list[PolymarketMarket]) -> list[ClassifiedMarket]:
    """Classify all markets against tracked queries."""
    classified: list[ClassifiedMarket] = []
    seen: set[str] = set()
    for market in markets:
        if market.market_id in seen:
            continue
        text = f"{market.question} {market.event_title}"
        for query in TRACKED_QUERIES:
            if _match_keywords(text, query.keywords):
                classified.append(classify_market(market, query))
                seen.add(market.market_id)
                break
    return classified


def cmd_markets() -> int:
    """Print active relevant prediction markets as JSON."""
    markets = fetch_relevant_markets()
    classified = _classify_all(markets)

    output = {
        "total": len(classified),
        "markets": [
            {
                "question": m.question,
                "category": m.category,
                "signal": m.signal,
                "probability": round(m.probability, 4),
                "sectors": list(m.affected_sectors),
                "reason": m.reason,
                "volume": round(m.volume, 2),
            }
            for m in sorted(classified, key=lambda m: m.volume, reverse=True)[:30]
        ],
        "as_of": datetime.now(tz=UTC).isoformat(timespec="seconds"),
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def cmd_summary() -> int:
    """Print aggregated prediction summary as JSON."""
    markets = fetch_relevant_markets()
    classified = _classify_all(markets)
    summary = build_prediction_summary(classified)

    output = {
        "total_markets": summary.total_markets,
        "relevant_markets": summary.relevant_markets,
        "overall_signal": summary.overall_signal,
        "favorable_count": summary.favorable_count,
        "unfavorable_count": summary.unfavorable_count,
        "neutral_count": summary.neutral_count,
        "markets_by_category": summary.markets_by_category,
        "affected_sectors": summary.affected_sectors,
        "top_markets": [
            {
                "question": m.question,
                "category": m.category,
                "signal": m.signal,
                "probability": round(m.probability, 4),
                "sectors": list(m.affected_sectors),
                "reason": m.reason,
            }
            for m in summary.top_markets
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
        case "markets":
            exit_code = cmd_markets()
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

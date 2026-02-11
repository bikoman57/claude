from __future__ import annotations

import json
import sys
from dataclasses import asdict

from app.news.categorizer import build_news_summary, categorize_article
from app.news.feeds import fetch_all_feeds
from app.news.journalists import load_journalist_ratings

USAGE = """\
Usage:
  uv run python -m app.news headlines      Latest headlines with sentiment
  uv run python -m app.news summary        Aggregated news summary
  uv run python -m app.news journalists    Journalist accuracy ratings
"""


def cmd_headlines() -> int:
    """Print latest headlines with sentiment classification."""
    articles = fetch_all_feeds()
    categorized = [categorize_article(a) for a in articles]

    for ca in categorized[:20]:
        sectors = ", ".join(ca.sectors) if ca.sectors else "general"
        print(  # noqa: T201
            f"[{ca.sentiment:<7}] [{sectors}] {ca.article.title}",
        )
        if ca.article.source:
            print(f"         Source: {ca.article.source}")  # noqa: T201
    return 0


def cmd_summary() -> int:
    """Print aggregated news summary as JSON."""
    articles = fetch_all_feeds()
    categorized = [categorize_article(a) for a in articles]
    summary = build_news_summary(categorized)

    output = {
        "total_articles": summary.total_articles,
        "sentiment": summary.sentiment,
        "bullish_count": summary.bullish_count,
        "bearish_count": summary.bearish_count,
        "neutral_count": summary.neutral_count,
        "sector_mentions": summary.sector_mentions,
        "top_headlines": [
            {
                "title": a.article.title,
                "sentiment": a.sentiment,
                "sectors": list(a.sectors),
                "relevance": a.relevance,
            }
            for a in summary.top_articles
        ],
        "as_of": summary.as_of,
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def cmd_journalists() -> int:
    """Print journalist accuracy ratings."""
    ratings = load_journalist_ratings()
    if not ratings:
        print("No journalist ratings recorded yet.")  # noqa: T201
        return 0

    sorted_ratings = sorted(ratings, key=lambda r: r.accuracy, reverse=True)
    print(json.dumps([asdict(r) for r in sorted_ratings], indent=2))  # noqa: T201
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]
    match command:
        case "headlines":
            exit_code = cmd_headlines()
        case "summary":
            exit_code = cmd_summary()
        case "journalists":
            exit_code = cmd_journalists()
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

from __future__ import annotations

import json
import sys
from dataclasses import asdict

from app.social.officials import (
    build_officials_summary,
    fetch_all_official_statements,
)
from app.social.reddit import fetch_reddit_summary

USAGE = """\
Usage:
  uv run python -m app.social reddit          Reddit sentiment summary
  uv run python -m app.social officials        Key figures statements
  uv run python -m app.social summary          Combined social summary
"""


def cmd_reddit() -> int:
    """Print Reddit sentiment summary."""
    summary = fetch_reddit_summary()
    if summary is None:
        print(  # noqa: T201
            "Reddit not configured. Set REDDIT_CLIENT_ID and "
            "REDDIT_CLIENT_SECRET in .env",
        )
        return 0
    print(json.dumps(asdict(summary), indent=2))  # noqa: T201
    return 0


def cmd_officials() -> int:
    """Print official statements summary."""
    statements = fetch_all_official_statements()
    summary = build_officials_summary(statements)
    output = {
        "fed_tone": summary.fed_tone,
        "policy_direction": summary.policy_direction,
        "total_statements": summary.total_statements,
        "statements": [
            {
                "speaker": s.speaker,
                "title": s.title,
                "sentiment": s.sentiment,
                "date": s.date,
            }
            for s in summary.statements[:10]
        ],
        "as_of": summary.as_of,
    }
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def cmd_summary() -> int:
    """Print combined social summary."""
    reddit = fetch_reddit_summary()
    statements = fetch_all_official_statements()
    officials = build_officials_summary(statements)

    output: dict[str, object] = {
        "officials": {
            "fed_tone": officials.fed_tone,
            "policy_direction": officials.policy_direction,
            "total_statements": officials.total_statements,
        },
        "as_of": officials.as_of,
    }

    if reddit is not None:
        output["reddit"] = {
            "overall_sentiment": reddit.overall_sentiment,
            "top_tickers": list(reddit.top_tickers),
            "subreddits": [
                {
                    "name": s.subreddit,
                    "sentiment": s.sentiment,
                    "posts": s.total_posts,
                }
                for s in reddit.subreddits
            ],
        }
    else:
        output["reddit"] = "not configured"

    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]
    match command:
        case "reddit":
            exit_code = cmd_reddit()
        case "officials":
            exit_code = cmd_officials()
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

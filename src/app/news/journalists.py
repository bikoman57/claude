from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

_DATA_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "journalist_ratings.json"
)


@dataclass(frozen=True, slots=True)
class JournalistRating:
    """Track journalist prediction accuracy."""

    name: str
    outlet: str
    articles_tracked: int
    correct_predictions: int
    accuracy: float
    last_updated: str


def load_journalist_ratings(
    path: Path | None = None,
) -> list[JournalistRating]:
    """Load journalist ratings from JSON file."""
    target = path or _DATA_PATH
    if not target.exists():
        return []
    data = json.loads(target.read_text())
    return [JournalistRating(**r) for r in data]


def save_journalist_ratings(
    ratings: list[JournalistRating],
    path: Path | None = None,
) -> None:
    """Save journalist ratings to JSON file."""
    target = path or _DATA_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([asdict(r) for r in ratings], indent=2))


def update_journalist_rating(
    name: str,
    outlet: str,
    was_correct: bool,
    path: Path | None = None,
) -> JournalistRating:
    """Update a journalist's accuracy rating."""
    ratings = load_journalist_ratings(path)

    existing = None
    for i, r in enumerate(ratings):
        if r.name == name and r.outlet == outlet:
            existing = (i, r)
            break

    now = datetime.now(tz=UTC).isoformat(timespec="seconds")

    if existing is not None:
        idx, old = existing
        tracked = old.articles_tracked + 1
        correct = old.correct_predictions + (1 if was_correct else 0)
        updated = JournalistRating(
            name=name,
            outlet=outlet,
            articles_tracked=tracked,
            correct_predictions=correct,
            accuracy=correct / tracked if tracked > 0 else 0.0,
            last_updated=now,
        )
        ratings[idx] = updated
    else:
        updated = JournalistRating(
            name=name,
            outlet=outlet,
            articles_tracked=1,
            correct_predictions=1 if was_correct else 0,
            accuracy=1.0 if was_correct else 0.0,
            last_updated=now,
        )
        ratings.append(updated)

    save_journalist_ratings(ratings, path)
    return updated

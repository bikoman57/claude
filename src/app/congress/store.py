"""JSON persistence for Congress trade data and member ratings."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.congress.fetcher import CongressTrade

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "congress"
_TRADES_PATH = _DATA_DIR / "trades.json"
_MEMBERS_PATH = _DATA_DIR / "member_ratings.json"
_FETCH_META_PATH = _DATA_DIR / "fetch_meta.json"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_trades(path: Path | None = None) -> list[CongressTrade]:
    """Load trades from JSON file."""
    p = path or _TRADES_PATH
    if not p.exists():
        return []

    data = json.loads(p.read_text())
    return [CongressTrade(**item) for item in data]


def save_trades(trades: list[CongressTrade], path: Path | None = None) -> None:
    """Save trades to JSON file."""
    _ensure_dir()
    p = path or _TRADES_PATH
    p.write_text(json.dumps([asdict(t) for t in trades], indent=2))


def load_member_ratings(path: Path | None = None) -> list[dict[str, object]]:
    """Load member ratings from JSON file."""
    p = path or _MEMBERS_PATH
    if not p.exists():
        return []
    return json.loads(p.read_text())  # type: ignore[no-any-return]


def save_member_ratings(
    ratings: list[dict[str, object]],
    path: Path | None = None,
) -> None:
    """Save member ratings to JSON file."""
    _ensure_dir()
    p = path or _MEMBERS_PATH
    p.write_text(json.dumps(ratings, indent=2))


def load_fetch_meta(path: Path | None = None) -> dict[str, str]:
    """Load fetch metadata (timestamps)."""
    p = path or _FETCH_META_PATH
    if not p.exists():
        return {}
    return json.loads(p.read_text())  # type: ignore[no-any-return]


def save_fetch_meta(meta: dict[str, str], path: Path | None = None) -> None:
    """Save fetch metadata."""
    _ensure_dir()
    p = path or _FETCH_META_PATH
    p.write_text(json.dumps(meta, indent=2))


def is_cache_stale(
    source: str,
    ttl_hours: int = 6,
    path: Path | None = None,
) -> bool:
    """Check if cached data for a source is stale."""
    meta = load_fetch_meta(path)
    last_fetch = meta.get(f"{source}_last_fetch")
    if not last_fetch:
        return True

    fetched_at = datetime.fromisoformat(last_fetch)
    return datetime.now(tz=UTC) - fetched_at > timedelta(hours=ttl_hours)

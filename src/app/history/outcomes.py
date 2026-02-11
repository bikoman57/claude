from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_OUTCOMES_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "outcomes.json"
)


@dataclass
class TradeOutcome:
    """A completed or in-progress trade with factor context."""

    leveraged_ticker: str
    underlying_ticker: str
    entry_date: str
    entry_price: float
    exit_date: str | None = None
    exit_price: float | None = None
    pl_pct: float | None = None
    win: bool | None = None
    factors_at_entry: dict[str, str] = field(default_factory=dict)


def load_outcomes(path: Path | None = None) -> list[TradeOutcome]:
    """Load all trade outcomes."""
    store = path or _OUTCOMES_PATH
    if not store.exists():
        return []
    raw: list[dict[str, object]] = json.loads(
        store.read_text(encoding="utf-8"),
    )
    return [TradeOutcome(**r) for r in raw]  # type: ignore[arg-type]


def save_outcomes(
    outcomes: list[TradeOutcome],
    path: Path | None = None,
) -> None:
    """Save all trade outcomes."""
    store = path or _OUTCOMES_PATH
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps([asdict(o) for o in outcomes], indent=2),
        encoding="utf-8",
    )


def record_entry(
    leveraged_ticker: str,
    underlying_ticker: str,
    entry_price: float,
    factors: dict[str, str] | None = None,
    path: Path | None = None,
) -> TradeOutcome:
    """Record a new trade entry."""
    outcomes = load_outcomes(path)
    outcome = TradeOutcome(
        leveraged_ticker=leveraged_ticker,
        underlying_ticker=underlying_ticker,
        entry_date=datetime.now(tz=UTC).isoformat(timespec="seconds"),
        entry_price=entry_price,
        factors_at_entry=factors or {},
    )
    outcomes.append(outcome)
    save_outcomes(outcomes, path)
    return outcome


def record_exit(
    leveraged_ticker: str,
    exit_price: float,
    path: Path | None = None,
) -> TradeOutcome | None:
    """Record a trade exit. Returns updated outcome or None if not found."""
    outcomes = load_outcomes(path)
    for outcome in outcomes:
        if outcome.leveraged_ticker == leveraged_ticker and outcome.exit_date is None:
            outcome.exit_date = datetime.now(tz=UTC).isoformat(
                timespec="seconds",
            )
            outcome.exit_price = exit_price
            outcome.pl_pct = (exit_price - outcome.entry_price) / outcome.entry_price
            outcome.win = outcome.pl_pct > 0
            save_outcomes(outcomes, path)
            return outcome
    return None


def get_completed_outcomes(
    path: Path | None = None,
) -> list[TradeOutcome]:
    """Get only completed trades (have exit_date)."""
    return [o for o in load_outcomes(path) if o.exit_date is not None]

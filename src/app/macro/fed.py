from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

FOMC_DATES_2025_2026 = [
    date(2025, 1, 29),
    date(2025, 3, 19),
    date(2025, 5, 7),
    date(2025, 6, 18),
    date(2025, 7, 30),
    date(2025, 9, 17),
    date(2025, 10, 29),
    date(2025, 12, 17),
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 5, 6),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 16),
]


@dataclass(frozen=True, slots=True)
class FedSummary:
    """Federal Reserve policy summary."""

    current_rate: float | None
    trajectory: str  # HIKING / PAUSING / CUTTING / UNKNOWN
    next_fomc: str | None  # ISO date string
    days_to_fomc: int | None


def classify_trajectory(rates: list[float]) -> str:
    """Classify rate trajectory from recent rate history.

    Args:
        rates: Recent FEDFUNDS values (oldest to newest).
    """
    if len(rates) < 2:
        return "UNKNOWN"
    recent = rates[-3:] if len(rates) >= 3 else rates
    changes = [
        recent[i] - recent[i - 1] for i in range(1, len(recent))
    ]
    if all(c > 0 for c in changes):
        return "HIKING"
    if all(c < 0 for c in changes):
        return "CUTTING"
    return "PAUSING"


def get_next_fomc(today: date | None = None) -> date | None:
    """Get the next FOMC meeting date."""
    ref = today or datetime.now(tz=UTC).date()
    for d in FOMC_DATES_2025_2026:
        if d >= ref:
            return d
    return None


def get_upcoming_fomc(
    count: int = 3,
    today: date | None = None,
) -> list[date]:
    """Get the next N FOMC meeting dates."""
    ref = today or datetime.now(tz=UTC).date()
    return [d for d in FOMC_DATES_2025_2026 if d >= ref][:count]


def build_fed_summary(
    current_rate: float | None,
    rate_history: list[float],
    today: date | None = None,
) -> FedSummary:
    """Build a FedSummary from rate data."""
    trajectory = classify_trajectory(rate_history)
    next_meeting = get_next_fomc(today)
    ref = today or datetime.now(tz=UTC).date()
    days = (next_meeting - ref).days if next_meeting else None
    return FedSummary(
        current_rate=current_rate,
        trajectory=trajectory,
        next_fomc=(
            next_meeting.isoformat() if next_meeting else None
        ),
        days_to_fomc=days,
    )

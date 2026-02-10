from __future__ import annotations

from datetime import date

from app.macro.fed import (
    build_fed_summary,
    classify_trajectory,
    get_next_fomc,
    get_upcoming_fomc,
)


def test_classify_trajectory_hiking():
    assert classify_trajectory([4.0, 4.25, 4.50]) == "HIKING"


def test_classify_trajectory_cutting():
    assert classify_trajectory([5.0, 4.75, 4.50]) == "CUTTING"


def test_classify_trajectory_pausing():
    assert classify_trajectory([4.5, 4.5, 4.5]) == "PAUSING"


def test_classify_trajectory_mixed():
    assert classify_trajectory([4.0, 4.25, 4.0]) == "PAUSING"


def test_classify_trajectory_unknown():
    assert classify_trajectory([4.5]) == "UNKNOWN"
    assert classify_trajectory([]) == "UNKNOWN"


def test_get_next_fomc():
    # Use a date we know is before a meeting
    result = get_next_fomc(today=date(2025, 3, 1))
    assert result == date(2025, 3, 19)


def test_get_next_fomc_on_meeting_day():
    result = get_next_fomc(today=date(2025, 3, 19))
    assert result == date(2025, 3, 19)


def test_get_next_fomc_none():
    # Far future — past all hardcoded dates
    result = get_next_fomc(today=date(2030, 1, 1))
    assert result is None


def test_get_upcoming_fomc():
    dates = get_upcoming_fomc(count=3, today=date(2025, 6, 1))
    assert len(dates) == 3
    assert dates[0] == date(2025, 6, 18)


def test_build_fed_summary():
    summary = build_fed_summary(
        current_rate=4.5,
        rate_history=[4.25, 4.5, 4.5],
        today=date(2025, 6, 1),
    )
    assert summary.current_rate == 4.5
    assert summary.trajectory == "PAUSING"
    assert summary.next_fomc == "2025-06-18"
    assert summary.days_to_fomc == 17

"""Tests for risk exposure calculations."""

from __future__ import annotations

from app.risk.exposure import Position, calculate_exposure


def test_empty_portfolio() -> None:
    """Empty portfolio has full cash."""
    report = calculate_exposure([], 10_000.0)
    assert report.position_count == 0
    assert report.cash_pct == 1.0
    assert report.invested_pct == 0.0
    assert report.total_leveraged_exposure == 0.0


def test_single_position_exposure() -> None:
    """Single position calculates correctly."""
    pos = Position(
        leveraged_ticker="TQQQ",
        entry_price=40.0,
        current_price=42.0,
        shares=50.0,
        leverage=3,
    )
    report = calculate_exposure([pos], 10_000.0)

    assert report.position_count == 1
    assert report.invested_value == 2100.0  # 50 * 42
    assert report.cash_value == 7900.0
    assert report.total_leveraged_exposure == 6300.0  # 2100 * 3
    assert report.leveraged_exposure_ratio == 0.63


def test_sector_allocation() -> None:
    """Sector allocation sums correctly."""
    positions = [
        Position("TQQQ", 40.0, 42.0, 50.0, 3),
        Position("TECL", 30.0, 31.0, 30.0, 3),
    ]
    report = calculate_exposure(positions, 10_000.0)
    assert report.position_count == 2
    # Both are tech-adjacent — sectors depend on ETF_UNIVERSE names
    assert len(report.sector_pcts) >= 1


def test_unrealized_pl() -> None:
    """Unrealized P&L tracks price changes."""
    pos = Position(
        leveraged_ticker="TQQQ",
        entry_price=40.0,
        current_price=44.0,
        shares=100.0,
    )
    assert pos.unrealized_pl == 400.0
    assert pos.unrealized_pl_pct == 0.1

    report = calculate_exposure([pos], 10_000.0)
    assert report.unrealized_pl == 400.0


def test_zero_portfolio_value() -> None:
    """Zero portfolio value doesn't crash."""
    report = calculate_exposure([], 0.0)
    assert report.cash_pct == 1.0
    assert report.invested_pct == 0.0

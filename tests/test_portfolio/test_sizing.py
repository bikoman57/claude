"""Tests for portfolio position sizing."""

from __future__ import annotations

from app.portfolio.sizing import fixed_fraction_size, kelly_size


def test_fixed_fraction_basic() -> None:
    """Fixed fraction with default 2% risk."""
    result = fixed_fraction_size(25_000.0, risk_pct=0.02, leverage=3)
    assert result.method == "fixed_fraction"
    assert result.position_value == 500.0  # 25K * 2%
    assert result.portfolio_pct == 0.02


def test_fixed_fraction_zero_portfolio() -> None:
    """Zero portfolio returns zero position."""
    result = fixed_fraction_size(0.0)
    assert result.position_value == 0.0
    assert result.portfolio_pct == 0.0


def test_fixed_fraction_shares_estimate() -> None:
    """Shares estimate uses entry price."""
    result = fixed_fraction_size(10_000.0, entry_price=50.0)
    assert result.shares_estimate == result.position_value / 50.0


def test_kelly_basic() -> None:
    """Kelly criterion with good win rate."""
    result = kelly_size(
        portfolio_value=25_000.0,
        win_rate=0.65,
        avg_win=0.12,
        avg_loss=0.08,
        fraction=0.5,
    )
    assert result.method == "kelly_50%"
    assert result.position_value > 0
    assert result.portfolio_pct > 0


def test_kelly_poor_edge() -> None:
    """Kelly with no edge returns zero."""
    result = kelly_size(
        portfolio_value=25_000.0,
        win_rate=0.30,
        avg_win=0.05,
        avg_loss=0.10,
        fraction=0.5,
    )
    assert result.position_value == 0.0


def test_kelly_zero_win_rate() -> None:
    """Kelly with zero win rate returns zero."""
    result = kelly_size(
        portfolio_value=25_000.0,
        win_rate=0.0,
        avg_win=0.10,
        avg_loss=0.08,
    )
    assert result.position_value == 0.0


def test_kelly_zero_loss() -> None:
    """Kelly with zero avg loss returns zero (division guard)."""
    result = kelly_size(
        portfolio_value=25_000.0,
        win_rate=0.65,
        avg_win=0.10,
        avg_loss=0.0,
    )
    assert result.position_value == 0.0

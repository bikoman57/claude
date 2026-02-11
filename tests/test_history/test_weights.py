from __future__ import annotations

import pytest

from app.history.outcomes import TradeOutcome
from app.history.weights import (
    FACTOR_NAMES,
    calculate_weights,
    format_learning_insights,
)


def _make_outcome(
    win: bool,
    factors: dict[str, str] | None = None,
) -> TradeOutcome:
    return TradeOutcome(
        leveraged_ticker="TQQQ",
        underlying_ticker="QQQ",
        entry_date="2025-01-01T00:00:00+00:00",
        entry_price=45.00,
        exit_date="2025-02-01T00:00:00+00:00",
        exit_price=49.50 if win else 40.00,
        pl_pct=0.1 if win else -0.111,
        win=win,
        factors_at_entry=factors or {},
    )


def test_calculate_weights_empty():
    weights = calculate_weights([])
    assert weights == []


def test_calculate_weights_all_neutral():
    outcomes = [_make_outcome(win=True), _make_outcome(win=False)]
    weights = calculate_weights(outcomes)
    assert len(weights) == len(FACTOR_NAMES)
    # All equal since no factor data provided
    for w in weights:
        assert w.weight == pytest.approx(1.0 / len(FACTOR_NAMES))


def test_calculate_weights_single_factor_dominates():
    # Drawdown favorable on wins, unfavorable on losses
    outcomes = [
        _make_outcome(True, {"drawdown_depth": "FAVORABLE"}),
        _make_outcome(True, {"drawdown_depth": "FAVORABLE"}),
        _make_outcome(False, {"drawdown_depth": "UNFAVORABLE"}),
        _make_outcome(False, {"drawdown_depth": "UNFAVORABLE"}),
    ]
    weights = calculate_weights(outcomes)
    drawdown_w = next(w for w in weights if w.name == "drawdown_depth")
    # Drawdown should have highest weight
    assert drawdown_w.weight > 0.5
    assert drawdown_w.favorable_wins == 2
    assert drawdown_w.favorable_total == 2
    assert drawdown_w.unfavorable_wins == 0
    assert drawdown_w.unfavorable_total == 2


def test_format_learning_insights():
    outcomes = [
        _make_outcome(True, {"drawdown_depth": "FAVORABLE"}),
    ]
    weights = calculate_weights(outcomes)
    text = format_learning_insights(weights, 1, 1, 10.0)
    assert "1 past trades" in text
    assert "Win rate: 100%" in text
    assert "+10.0%" in text


def test_format_learning_insights_empty():
    text = format_learning_insights([], 0, 0, 0.0)
    assert "unavailable" in text

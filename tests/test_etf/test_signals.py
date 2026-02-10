from __future__ import annotations

from app.etf.drawdown import DrawdownResult
from app.etf.signals import SignalState, evaluate_active_position, evaluate_signal
from app.etf.universe import ETFMapping


def _mapping() -> ETFMapping:
    return ETFMapping("TQQQ", "QQQ", "Test", 3.0, 0.05, 0.03, 0.10)


def _drawdown(pct: float) -> DrawdownResult:
    return DrawdownResult(
        ticker="QQQ",
        current_price=100.0 * (1 + pct),
        ath_price=100.0,
        ath_date="2025-01-01",
        drawdown_pct=pct,
        as_of="2025-06-01T00:00:00+00:00",
    )


def test_evaluate_signal_watch():
    sig = evaluate_signal(_mapping(), _drawdown(-0.01))
    assert sig.state == SignalState.WATCH


def test_evaluate_signal_alert():
    sig = evaluate_signal(_mapping(), _drawdown(-0.04))
    assert sig.state == SignalState.ALERT


def test_evaluate_signal_signal():
    sig = evaluate_signal(_mapping(), _drawdown(-0.06))
    assert sig.state == SignalState.SIGNAL


def test_evaluate_signal_at_ath():
    sig = evaluate_signal(_mapping(), _drawdown(0.0))
    assert sig.state == SignalState.WATCH


def test_evaluate_signal_exact_threshold():
    sig = evaluate_signal(_mapping(), _drawdown(-0.05))
    assert sig.state == SignalState.SIGNAL


def test_evaluate_signal_exact_alert():
    sig = evaluate_signal(_mapping(), _drawdown(-0.03))
    assert sig.state == SignalState.ALERT


def test_evaluate_active_position_below_target():
    sig = evaluate_signal(_mapping(), _drawdown(-0.06))
    sig.state = SignalState.ACTIVE
    sig.leveraged_entry_price = 40.0

    result = evaluate_active_position(sig, 43.0)
    assert result.state == SignalState.ACTIVE
    assert result.current_pl_pct is not None
    assert result.current_pl_pct < 0.10


def test_evaluate_active_position_hits_target():
    sig = evaluate_signal(_mapping(), _drawdown(-0.06))
    sig.state = SignalState.ACTIVE
    sig.leveraged_entry_price = 40.0

    result = evaluate_active_position(sig, 44.0)
    assert result.state == SignalState.TARGET
    assert result.current_pl_pct is not None
    assert result.current_pl_pct >= 0.10


def test_evaluate_active_no_entry_price():
    sig = evaluate_signal(_mapping(), _drawdown(-0.06))
    sig.state = SignalState.ACTIVE
    result = evaluate_active_position(sig, 50.0)
    assert result.state == SignalState.ACTIVE

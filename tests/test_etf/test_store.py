from __future__ import annotations

from pathlib import Path

from app.etf.signals import Signal, SignalState
from app.etf.store import (
    get_actionable_signals,
    get_active_signals,
    load_signals,
    save_signals,
)


def _signal(ticker: str = "TQQQ", state: SignalState = SignalState.WATCH) -> Signal:
    return Signal(
        leveraged_ticker=ticker,
        underlying_ticker="QQQ",
        state=state,
        underlying_drawdown_pct=-0.05,
        underlying_ath=500.0,
        underlying_current=475.0,
    )


def test_save_and_load_roundtrip(tmp_path: Path):
    path = tmp_path / "signals.json"
    signals = [_signal("TQQQ", SignalState.SIGNAL), _signal("SOXL", SignalState.WATCH)]
    save_signals(signals, path)
    loaded = load_signals(path)
    assert len(loaded) == 2
    assert loaded[0].leveraged_ticker == "TQQQ"
    assert loaded[0].state == SignalState.SIGNAL
    assert loaded[1].state == SignalState.WATCH


def test_load_empty_file(tmp_path: Path):
    path = tmp_path / "nonexistent.json"
    assert load_signals(path) == []


def test_get_active_signals(tmp_path: Path):
    path = tmp_path / "signals.json"
    signals = [
        _signal("TQQQ", SignalState.ACTIVE),
        _signal("SOXL", SignalState.WATCH),
        _signal("UPRO", SignalState.ACTIVE),
    ]
    save_signals(signals, path)
    active = get_active_signals(path)
    assert len(active) == 2
    assert all(s.state == SignalState.ACTIVE for s in active)


def test_get_actionable_signals(tmp_path: Path):
    path = tmp_path / "signals.json"
    signals = [
        _signal("TQQQ", SignalState.SIGNAL),
        _signal("SOXL", SignalState.TARGET),
        _signal("UPRO", SignalState.WATCH),
    ]
    save_signals(signals, path)
    actionable = get_actionable_signals(path)
    assert len(actionable) == 2
    tickers = {s.leveraged_ticker for s in actionable}
    assert tickers == {"TQQQ", "SOXL"}

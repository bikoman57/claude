from __future__ import annotations

from app.strategy.backtest import BacktestConfig, BacktestResult, BacktestTrade
from app.strategy.store import list_backtests, load_backtest, save_backtest


def _make_result() -> BacktestResult:
    config = BacktestConfig(
        underlying_ticker="QQQ",
        leverage=3.0,
        entry_threshold=0.05,
        profit_target=0.10,
        stop_loss=0.15,
        period="2y",
    )
    trades = (
        BacktestTrade(
            entry_day=10,
            exit_day=20,
            entry_price=100.0,
            exit_price=110.0,
            drawdown_at_entry=0.06,
            leveraged_return=0.30,
            exit_reason="target",
        ),
        BacktestTrade(
            entry_day=50,
            exit_day=60,
            entry_price=105.0,
            exit_price=100.0,
            drawdown_at_entry=0.08,
            leveraged_return=-0.1429,
            exit_reason="stop",
        ),
    )
    return BacktestResult(
        config=config,
        trades=trades,
        total_return=0.15,
        sharpe_ratio=1.2,
        max_drawdown=0.14,
        win_rate=0.5,
        avg_gain=0.30,
        avg_loss=-0.1429,
        total_days=500,
    )


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.strategy.store._DATA_DIR", tmp_path / "backtests",
    )
    result = _make_result()
    path = save_backtest(result)

    assert path.exists()
    assert "QQQ" in path.name

    loaded = load_backtest(path)
    assert loaded.config.underlying_ticker == "QQQ"
    assert loaded.total_return == 0.15
    assert loaded.sharpe_ratio == 1.2
    assert len(loaded.trades) == 2
    assert loaded.trades[0].exit_reason == "target"
    assert loaded.trades[1].exit_reason == "stop"


def test_list_backtests_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.strategy.store._DATA_DIR", tmp_path / "backtests",
    )
    assert list_backtests() == []


def test_list_backtests_filter(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.strategy.store._DATA_DIR", tmp_path / "backtests",
    )

    result = _make_result()
    save_backtest(result)

    # Create another file for a different ticker
    (tmp_path / "backtests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backtests" / "SPY_5pct_2026-01-01.json").write_text("{}")

    all_files = list_backtests()
    assert len(all_files) == 2

    qqq_files = list_backtests("QQQ")
    assert len(qqq_files) == 1
    assert "QQQ" in qqq_files[0].name

    spy_files = list_backtests("SPY")
    assert len(spy_files) == 1
    assert "SPY" in spy_files[0].name


def test_save_creates_directory(tmp_path, monkeypatch):
    new_dir = tmp_path / "nested" / "backtests"
    monkeypatch.setattr("app.strategy.store._DATA_DIR", new_dir)

    result = _make_result()
    path = save_backtest(result)
    assert path.exists()
    assert new_dir.exists()


def test_roundtrip_preserves_none_sharpe(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.strategy.store._DATA_DIR", tmp_path / "backtests",
    )
    config = BacktestConfig(
        underlying_ticker="SPY",
        leverage=3.0,
        entry_threshold=0.05,
        profit_target=0.10,
        stop_loss=0.15,
        period="2y",
    )
    result = BacktestResult(
        config=config,
        trades=(),
        total_return=0.0,
        sharpe_ratio=None,
        max_drawdown=0.0,
        win_rate=None,
        avg_gain=None,
        avg_loss=None,
        total_days=100,
    )
    path = save_backtest(result)
    loaded = load_backtest(path)
    assert loaded.sharpe_ratio is None
    assert loaded.win_rate is None

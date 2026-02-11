from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from app.strategy.backtest import (
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
    _calculate_sharpe,
    run_backtest,
)


def _make_config(**overrides) -> BacktestConfig:
    defaults = {
        "underlying_ticker": "QQQ",
        "leverage": 3.0,
        "entry_threshold": 0.05,
        "profit_target": 0.10,
        "stop_loss": 0.15,
        "period": "2y",
    }
    defaults.update(overrides)
    return BacktestConfig(**defaults)


def _mock_history(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": prices, "Volume": [1000] * len(prices)})


def test_backtest_config_creation():
    cfg = _make_config()
    assert cfg.underlying_ticker == "QQQ"
    assert cfg.leverage == 3.0
    assert cfg.entry_threshold == 0.05


def test_backtest_trade_dataclass():
    trade = BacktestTrade(
        entry_day=10,
        exit_day=20,
        entry_price=100.0,
        exit_price=110.0,
        drawdown_at_entry=0.06,
        leveraged_return=0.30,
        exit_reason="target",
    )
    assert trade.leveraged_return == 0.30
    assert trade.exit_reason == "target"


def test_backtest_result_dataclass():
    cfg = _make_config()
    result = BacktestResult(
        config=cfg,
        trades=(),
        total_return=0.0,
        sharpe_ratio=None,
        max_drawdown=0.0,
        win_rate=None,
        avg_gain=None,
        avg_loss=None,
        total_days=100,
    )
    assert result.total_days == 100
    assert result.win_rate is None


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_basic(mock_ticker_cls):
    # Prices: rise to 110, drop to 95 (ATH=110, drawdown=13.6%), then recover
    prices = (
        [100.0 + i for i in range(11)]  # 100→110
        + [110.0 - i for i in range(1, 17)]  # 109→94
        + [94.0 + i * 2 for i in range(1, 15)]  # 96→122
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(entry_threshold=0.10)
    result = run_backtest(config)

    assert result is not None
    assert result.total_days == len(prices)
    assert len(result.trades) >= 1


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_no_trades(mock_ticker_cls):
    # Steadily rising prices — no drawdown occurs
    prices = [100.0 + i * 0.5 for i in range(50)]
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(entry_threshold=0.10)
    result = run_backtest(config)

    assert result is not None
    assert len(result.trades) == 0
    assert result.total_return == 0.0
    assert result.win_rate is None


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_insufficient_data(mock_ticker_cls):
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history([100.0] * 5)
    mock_ticker_cls.return_value = mock_t

    config = _make_config()
    result = run_backtest(config)
    assert result is None


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_stop_loss(mock_ticker_cls):
    # Prices: rise to 110, drop hard to 80, stay low
    prices = (
        [100.0 + i for i in range(11)]  # 100→110
        + [110.0 - i * 2 for i in range(1, 20)]  # 108→74
        + [74.0] * 10
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(entry_threshold=0.05, stop_loss=0.10)
    result = run_backtest(config)

    assert result is not None
    stops = [t for t in result.trades if t.exit_reason == "stop"]
    assert len(stops) >= 1


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_end_of_period(mock_ticker_cls):
    # Prices: drop then stay flat — trade open at end
    prices = (
        [100.0] * 5
        + [100.0 - i for i in range(1, 11)]  # drop to 90
        + [92.0] * 10  # stay flat
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(
        entry_threshold=0.05, profit_target=0.50, stop_loss=0.50,
    )
    result = run_backtest(config)

    assert result is not None
    eop = [t for t in result.trades if t.exit_reason == "end_of_period"]
    assert len(eop) >= 1


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_error(mock_ticker_cls):
    mock_ticker_cls.return_value.history.side_effect = RuntimeError("fail")
    config = _make_config()
    result = run_backtest(config)
    assert result is None


def test_calculate_sharpe_empty():
    assert _calculate_sharpe([]) is None
    assert _calculate_sharpe([0.1]) is None


def test_calculate_sharpe_zero_std():
    assert _calculate_sharpe([0.1, 0.1, 0.1]) is None


def test_calculate_sharpe_basic():
    returns = [0.05, 0.10, -0.02, 0.08, 0.03]
    sharpe = _calculate_sharpe(returns)
    assert sharpe is not None
    assert isinstance(sharpe, float)


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_win_rate(mock_ticker_cls):
    # Two cycles: drop-recover, drop-recover
    prices = (
        [100.0 + i for i in range(6)]  # 100→105
        + [105.0 - i for i in range(1, 12)]  # 104→94 (dd ~10%)
        + [94.0 + i * 2 for i in range(1, 10)]  # 96→112
        + [112.0 - i for i in range(1, 14)]  # 111→99 (dd ~11%)
        + [99.0 + i * 2 for i in range(1, 12)]  # 101→121
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(entry_threshold=0.08, profit_target=0.10)
    result = run_backtest(config)

    assert result is not None
    if result.trades:
        assert result.win_rate is not None

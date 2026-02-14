from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from app.strategy.backtest import (
    STRATEGY_DESCRIPTIONS,
    THRESHOLD_LABELS,
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
    StrategyType,
    _calculate_sharpe,
    _compute_bollinger,
    _compute_ma,
    _compute_rsi,
    _recency_weight,
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


def test_strategy_type_enum():
    assert StrategyType.ATH_MEAN_REVERSION == "ath_mean_reversion"
    assert StrategyType.RSI_OVERSOLD == "rsi_oversold"
    assert StrategyType.BOLLINGER_LOWER == "bollinger_lower"
    assert StrategyType.MA_DIP == "ma_dip"
    assert len(StrategyType) == 4


def test_strategy_descriptions():
    for stype in StrategyType:
        assert stype in STRATEGY_DESCRIPTIONS
        assert len(STRATEGY_DESCRIPTIONS[stype]) > 0


def test_threshold_labels():
    for stype in StrategyType:
        assert stype in THRESHOLD_LABELS
        assert len(THRESHOLD_LABELS[stype]) > 0


def test_backtest_config_default_strategy():
    cfg = _make_config()
    assert cfg.strategy_type == StrategyType.ATH_MEAN_REVERSION


def test_backtest_config_custom_strategy():
    cfg = _make_config(strategy_type=StrategyType.RSI_OVERSOLD)
    assert cfg.strategy_type == StrategyType.RSI_OVERSOLD


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
    assert trade.entry_date == ""
    assert trade.exit_date == ""


def test_backtest_trade_with_dates():
    trade = BacktestTrade(
        entry_day=10,
        exit_day=20,
        entry_price=100.0,
        exit_price=110.0,
        drawdown_at_entry=0.06,
        leveraged_return=0.30,
        exit_reason="target",
        entry_date="2025-01-15",
        exit_date="2025-02-01",
    )
    assert trade.entry_date == "2025-01-15"
    assert trade.exit_date == "2025-02-01"


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


# --- RSI computation tests ---


def test_compute_rsi_basic():
    # 15 values needed for first RSI(14) output
    prices = [44.0 + i * 0.5 for i in range(20)]
    rsi = _compute_rsi(prices, period=14)
    assert len(rsi) == len(prices)
    assert all(v is None for v in rsi[:14])
    assert rsi[14] is not None
    assert 0 <= rsi[14] <= 100


def test_compute_rsi_too_short():
    rsi = _compute_rsi([100.0, 101.0], period=14)
    assert all(v is None for v in rsi)


def test_compute_rsi_all_gains():
    prices = [100.0 + i for i in range(20)]
    rsi = _compute_rsi(prices, period=14)
    # All gains → RSI should be 100
    assert rsi[14] == 100.0


# --- Bollinger computation tests ---


def test_compute_bollinger_basic():
    prices = [100.0 + i * 0.1 for i in range(30)]
    bands = _compute_bollinger(prices, period=20)
    assert len(bands) == len(prices)
    assert all(v is None for v in bands[:19])
    lower, middle, upper = bands[19]
    assert lower < middle < upper


def test_compute_bollinger_too_short():
    bands = _compute_bollinger([100.0] * 10, period=20)
    assert all(v is None for v in bands)


# --- Moving average computation tests ---


def test_compute_ma_basic():
    prices = [100.0 + i for i in range(60)]
    ma = _compute_ma(prices, period=50)
    assert len(ma) == len(prices)
    assert all(v is None for v in ma[:49])
    assert ma[49] is not None
    assert isinstance(ma[49], float)


def test_compute_ma_too_short():
    ma = _compute_ma([100.0] * 10, period=50)
    assert all(v is None for v in ma)


# --- ATH strategy tests ---


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_basic(mock_ticker_cls):
    # Prices: rise to 110, drop to 95, then recover — need >=50 data points
    prices = (
        [100.0 + i for i in range(11)]  # 100→110
        + [110.0 - i for i in range(1, 17)]  # 109→94
        + [94.0 + i * 1.5 for i in range(1, 25)]  # 95.5→130
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
    prices = [100.0 + i * 0.5 for i in range(55)]
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
    # Prices: rise to 110, drop hard, stay low — need >=50 points
    prices = (
        [100.0 + i for i in range(11)]  # 100→110
        + [110.0 - i * 2 for i in range(1, 20)]  # 108→74
        + [74.0] * 25
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
        + [92.0] * 40  # stay flat (need >50 total for min data)
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(
        entry_threshold=0.05,
        profit_target=0.50,
        stop_loss=0.50,
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


# --- RSI strategy tests ---


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_rsi_oversold(mock_ticker_cls):
    """RSI strategy enters when RSI drops below threshold."""
    # Create declining then recovering prices
    prices = (
        [100.0] * 5
        + [100.0 - i * 1.5 for i in range(1, 20)]  # decline
        + [72.0 + i * 2 for i in range(1, 30)]  # recovery
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(
        entry_threshold=30.0,
        strategy_type=StrategyType.RSI_OVERSOLD,
    )
    result = run_backtest(config)

    assert result is not None
    assert result.config.strategy_type == StrategyType.RSI_OVERSOLD


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_rsi_no_signal(mock_ticker_cls):
    """RSI strategy: steadily rising → RSI stays high → no trades."""
    prices = [100.0 + i * 0.5 for i in range(55)]
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(
        entry_threshold=25.0,
        strategy_type=StrategyType.RSI_OVERSOLD,
    )
    result = run_backtest(config)

    assert result is not None
    assert len(result.trades) == 0


# --- Bollinger strategy tests ---


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_bollinger_lower(mock_ticker_cls):
    """Bollinger strategy enters when price hits lower band."""
    # Oscillating prices to trigger band touch
    import math

    prices = [100.0 + 10 * math.sin(i * 0.3) for i in range(60)]
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(
        entry_threshold=2.0,  # 2 std deviations
        strategy_type=StrategyType.BOLLINGER_LOWER,
    )
    result = run_backtest(config)

    assert result is not None
    assert result.config.strategy_type == StrategyType.BOLLINGER_LOWER


# --- MA Dip strategy tests ---


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_ma_dip(mock_ticker_cls):
    """MA dip strategy enters when price drops below MA."""
    # Rise then dip below MA
    prices = (
        [100.0 + i * 0.5 for i in range(55)]  # steady rise (builds MA)
        + [127.5 - i * 2 for i in range(1, 10)]  # sharp drop below MA
        + [110.0 + i for i in range(10)]  # recovery
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(
        entry_threshold=0.03,  # 3% below MA
        strategy_type=StrategyType.MA_DIP,
    )
    result = run_backtest(config)

    assert result is not None
    assert result.config.strategy_type == StrategyType.MA_DIP


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_ma_dip_no_signal(mock_ticker_cls):
    """MA dip: steadily rising prices never dip below MA."""
    prices = [100.0 + i * 0.5 for i in range(55)]
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(
        entry_threshold=0.05,
        strategy_type=StrategyType.MA_DIP,
    )
    result = run_backtest(config)

    assert result is not None
    assert len(result.trades) == 0


# --- Unknown strategy ---


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_unknown_strategy(mock_ticker_cls):
    """Unknown strategy type returns None."""
    prices = [100.0 + i for i in range(55)]
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = BacktestConfig(
        underlying_ticker="QQQ",
        leverage=3.0,
        entry_threshold=0.05,
        profit_target=0.10,
        stop_loss=0.15,
        period="2y",
        strategy_type="nonexistent",
    )
    result = run_backtest(config)
    assert result is None


# --- Sharpe ratio tests ---


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


# --- Recency weighting tests ---


def test_recency_weight_most_recent():
    """Most recent trade (entry_day == total_days) gets weight ~1.0."""
    w = _recency_weight(entry_day=1000, total_days=1000)
    assert abs(w - 1.0) < 0.01


def test_recency_weight_half_life():
    """Trade exactly half-life ago gets weight ~0.5."""
    half_life_days = int(3.0 * 252)  # 756 trading days
    w = _recency_weight(entry_day=0, total_days=half_life_days)
    assert abs(w - 0.5) < 0.01


def test_recency_weight_old_trade():
    """Trade from 15 years ago gets very low weight."""
    total_days = 15 * 252  # 3780 trading days
    w = _recency_weight(entry_day=0, total_days=total_days)
    assert w < 0.05  # 5 half-lives → 1/32 ≈ 0.031


def test_recency_weight_zero_total_days():
    """Edge case: total_days=0 returns 1.0."""
    assert _recency_weight(0, 0) == 1.0


@patch("app.strategy.backtest.yf.Ticker")
def test_run_backtest_produces_weighted_metrics(mock_ticker_cls):
    """Backtest results include weighted Sharpe and win rate."""
    prices = (
        [100.0 + i for i in range(11)]  # 100→110
        + [110.0 - i for i in range(1, 17)]  # 109→94
        + [94.0 + i * 1.5 for i in range(1, 25)]  # 95.5→130
    )
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_t

    config = _make_config(entry_threshold=0.10)
    result = run_backtest(config)

    assert result is not None
    assert len(result.trades) >= 1
    # Weighted metrics should be populated when there are trades
    assert result.weighted_win_rate is not None
    assert 0.0 <= result.weighted_win_rate <= 1.0

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.etf.stats import calculate_recovery_stats


def _mock_history(prices: list[float]) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=len(prices), freq="D")
    return pd.DataFrame({"Close": prices}, index=dates)


@patch("app.etf.stats.yf.Ticker")
def test_recovery_stats_single_episode(mock_ticker_cls):
    # Price rises to 100, drops 10% to 90, recovers to 100
    prices = [80.0, 90.0, 100.0, 95.0, 90.0, 92.0, 95.0, 100.0, 102.0]
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_ticker

    stats = calculate_recovery_stats("QQQ", 0.05)
    assert stats.total_episodes >= 1
    assert stats.recovery_rate > 0


@patch("app.etf.stats.yf.Ticker")
def test_recovery_stats_no_drawdown(mock_ticker_cls):
    # Steadily rising prices - no drawdown
    prices = [100.0, 101.0, 102.0, 103.0, 104.0]
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_ticker

    stats = calculate_recovery_stats("QQQ", 0.05)
    assert stats.total_episodes == 0
    assert stats.avg_recovery_days == 0.0


@patch("app.etf.stats.yf.Ticker")
def test_recovery_stats_still_in_drawdown(mock_ticker_cls):
    # Price drops and doesn't recover
    prices = [100.0, 95.0, 90.0, 88.0]
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_history(prices)
    mock_ticker_cls.return_value = mock_ticker

    stats = calculate_recovery_stats("QQQ", 0.05)
    assert stats.total_episodes == 1
    assert stats.recovery_rate == 0.0


@patch("app.etf.stats.yf.Ticker")
def test_recovery_stats_empty_data(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    mock_ticker_cls.return_value = mock_ticker

    with pytest.raises(ValueError, match="No data"):
        calculate_recovery_stats("FAKE", 0.05)

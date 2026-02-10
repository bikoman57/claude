from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.etf.drawdown import calculate_all_drawdowns, calculate_drawdown


def _mock_history(prices: list[float]) -> pd.DataFrame:
    """Create a mock yfinance history DataFrame."""
    dates = pd.date_range("2025-01-01", periods=len(prices), freq="D")
    return pd.DataFrame({"Close": prices}, index=dates)


@patch("app.etf.drawdown.yf.Ticker")
def test_calculate_drawdown_at_ath(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_history([100.0, 105.0, 110.0])
    mock_ticker_cls.return_value = mock_ticker

    result = calculate_drawdown("QQQ")
    assert result.ticker == "QQQ"
    assert result.ath_price == 110.0
    assert result.current_price == 110.0
    assert result.drawdown_pct == pytest.approx(0.0)


@patch("app.etf.drawdown.yf.Ticker")
def test_calculate_drawdown_below_ath(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _mock_history([100.0, 110.0, 104.5])
    mock_ticker_cls.return_value = mock_ticker

    result = calculate_drawdown("QQQ")
    assert result.ath_price == 110.0
    assert result.current_price == 104.5
    assert result.drawdown_pct == pytest.approx(-0.05, abs=0.001)


@patch("app.etf.drawdown.yf.Ticker")
def test_calculate_drawdown_empty_data(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    mock_ticker_cls.return_value = mock_ticker

    with pytest.raises(ValueError, match="No historical data"):
        calculate_drawdown("FAKE")


@patch("app.etf.drawdown.yf.Ticker")
def test_calculate_all_drawdowns_skips_errors(mock_ticker_cls):
    def side_effect(ticker):
        mock = MagicMock()
        if ticker == "GOOD":
            mock.history.return_value = _mock_history([100.0, 95.0])
        else:
            mock.history.return_value = pd.DataFrame()
        return mock

    mock_ticker_cls.side_effect = side_effect
    results = calculate_all_drawdowns(["GOOD", "BAD"])
    assert len(results) == 1
    assert results[0].ticker == "GOOD"

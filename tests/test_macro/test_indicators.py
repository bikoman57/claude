from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from app.macro.indicators import classify_vix, fetch_fred_latest, fetch_vix


def test_classify_vix_low():
    assert classify_vix(12.0) == "LOW"


def test_classify_vix_normal():
    assert classify_vix(17.5) == "NORMAL"


def test_classify_vix_elevated():
    assert classify_vix(25.0) == "ELEVATED"


def test_classify_vix_extreme():
    assert classify_vix(35.0) == "EXTREME"


@patch("app.macro.indicators.yf.Ticker")
def test_fetch_vix(mock_ticker_cls):
    mock_ticker = MagicMock()
    dates = pd.date_range("2025-01-01", periods=3, freq="D")
    mock_ticker.history.return_value = pd.DataFrame(
        {"Close": [22.5, 23.0, 21.8]},
        index=dates,
    )
    mock_ticker_cls.return_value = mock_ticker

    vix = fetch_vix()
    assert vix == 21.8
    mock_ticker_cls.assert_called_once_with("^VIX")


@patch("app.macro.indicators.httpx.Client")
def test_fetch_fred_latest(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "observations": [{"value": "3.5"}],
    }
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    result = fetch_fred_latest("FEDFUNDS", "test_key")
    assert result == 3.5


@patch("app.macro.indicators.httpx.Client")
def test_fetch_fred_latest_no_data(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"observations": []}
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    result = fetch_fred_latest("FAKE", "test_key")
    assert result is None


@patch("app.macro.indicators.httpx.Client")
def test_fetch_fred_latest_dot_value(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "observations": [{"value": "."}],
    }
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    result = fetch_fred_latest("STALE", "test_key")
    assert result is None

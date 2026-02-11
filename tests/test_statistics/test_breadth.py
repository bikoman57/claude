from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from app.statistics.breadth import (
    analyze_vix_term_structure,
    detect_volume_spikes,
    fetch_put_call_ratio,
)


def _mock_history(
    prices: list[float],
    volumes: list[int] | None = None,
) -> pd.DataFrame:
    if volumes is None:
        volumes = [1000] * len(prices)
    return pd.DataFrame({"Close": prices, "Volume": volumes})


@patch("app.statistics.breadth.yf.Ticker")
def test_fetch_put_call_ratio(mock_ticker_cls):
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history([0.85, 0.90, 0.95])
    mock_ticker_cls.return_value = mock_t

    pcr = fetch_put_call_ratio()
    assert pcr is not None
    assert pcr == 0.95


@patch("app.statistics.breadth.yf.Ticker")
def test_fetch_put_call_ratio_no_data(mock_ticker_cls):
    mock_t = MagicMock()
    mock_t.history.return_value = _mock_history([])
    mock_ticker_cls.return_value = mock_t

    pcr = fetch_put_call_ratio()
    assert pcr is None


@patch("app.statistics.breadth.yf.Ticker")
def test_vix_term_contango(mock_ticker_cls):
    # VIX < VIX3M * 0.95 → CONTANGO
    def make_ticker(ticker_name):
        mock_t = MagicMock()
        if ticker_name == "^VIX":
            mock_t.history.return_value = _mock_history([18.0])
        else:
            mock_t.history.return_value = _mock_history([22.0])
        return mock_t

    mock_ticker_cls.side_effect = make_ticker
    result = analyze_vix_term_structure()
    assert result == "CONTANGO"


@patch("app.statistics.breadth.yf.Ticker")
def test_vix_term_backwardation(mock_ticker_cls):
    # VIX > VIX3M * 1.05 → BACKWARDATION
    def make_ticker(ticker_name):
        mock_t = MagicMock()
        if ticker_name == "^VIX":
            mock_t.history.return_value = _mock_history([30.0])
        else:
            mock_t.history.return_value = _mock_history([22.0])
        return mock_t

    mock_ticker_cls.side_effect = make_ticker
    result = analyze_vix_term_structure()
    assert result == "BACKWARDATION"


@patch("app.statistics.breadth.yf.Ticker")
def test_detect_volume_spikes(mock_ticker_cls):
    mock_t = MagicMock()
    # Normal volumes then a spike on last day
    volumes = [1000, 1000, 1000, 1000, 1000, 5000]
    mock_t.history.return_value = _mock_history(
        [100.0] * 6,
        volumes,
    )
    mock_ticker_cls.return_value = mock_t

    spikes = detect_volume_spikes(["SPY"])
    assert len(spikes) == 1
    assert spikes[0].ticker == "SPY"
    assert spikes[0].volume_ratio >= 2.0


@patch("app.statistics.breadth.yf.Ticker")
def test_detect_no_volume_spikes(mock_ticker_cls):
    mock_t = MagicMock()
    volumes = [1000, 1000, 1000, 1000, 1000, 1000]
    mock_t.history.return_value = _mock_history(
        [100.0] * 6,
        volumes,
    )
    mock_ticker_cls.return_value = mock_t

    spikes = detect_volume_spikes(["SPY"])
    assert len(spikes) == 0

from __future__ import annotations

from app.sec.holdings import (
    get_all_unique_holdings,
    get_holding_by_ticker,
    get_holdings,
)


def test_get_holdings_qqq():
    holdings = get_holdings("QQQ")
    assert len(holdings) == 21
    tickers = [h.ticker for h in holdings]
    assert "AAPL" in tickers
    assert "NVDA" in tickers


def test_get_holdings_iwm():
    # IWM has small-cap holdings tracked
    holdings = get_holdings("IWM")
    assert len(holdings) == 5
    tickers = [h.ticker for h in holdings]
    assert "ROKU" in tickers


def test_get_holdings_unknown():
    assert get_holdings("FAKE") == []


def test_get_holding_by_ticker():
    h = get_holding_by_ticker("AAPL")
    assert h is not None
    assert h.cik == "0000320193"
    assert h.name == "Apple Inc."


def test_get_holding_by_ticker_unknown():
    assert get_holding_by_ticker("FAKE") is None


def test_get_all_unique_holdings():
    holdings = get_all_unique_holdings()
    tickers = [h.ticker for h in holdings]
    # NVDA appears in QQQ, SPY, SOXX, XLK — should appear once
    assert tickers.count("NVDA") == 1
    # Should have many unique holdings
    assert len(holdings) > 15

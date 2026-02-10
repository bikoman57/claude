from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import yfinance as yf


@dataclass(frozen=True, slots=True)
class DrawdownResult:
    """Result of a drawdown calculation for one underlying index."""

    ticker: str
    current_price: float
    ath_price: float
    ath_date: str
    drawdown_pct: float
    as_of: str


def calculate_drawdown(ticker: str, period: str = "5y") -> DrawdownResult:
    """Calculate the current drawdown from all-time high for a ticker."""
    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    if hist.empty:
        msg = f"No historical data for {ticker}"
        raise ValueError(msg)

    ath_price = float(hist["Close"].max())
    ath_date = str(hist["Close"].idxmax().date())
    current_price = float(hist["Close"].iloc[-1])
    drawdown_pct = (current_price - ath_price) / ath_price

    return DrawdownResult(
        ticker=ticker,
        current_price=current_price,
        ath_price=ath_price,
        ath_date=ath_date,
        drawdown_pct=drawdown_pct,
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )


def calculate_all_drawdowns(
    tickers: list[str],
    period: str = "5y",
) -> list[DrawdownResult]:
    """Calculate drawdowns for multiple tickers."""
    results: list[DrawdownResult] = []
    for ticker in tickers:
        try:
            results.append(calculate_drawdown(ticker, period))
        except ValueError as e:
            print(f"Warning: {ticker}: {e}")  # noqa: T201
    return results

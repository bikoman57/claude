from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import yfinance as yf

_YIELD_TICKERS = {
    "us_3m": "^IRX",
    "us_5y": "^FVX",
    "us_10y": "^TNX",
    "us_30y": "^TYX",
}


@dataclass(frozen=True, slots=True)
class YieldCurve:
    """Treasury yield curve snapshot."""

    us_3m: float | None
    us_5y: float | None
    us_10y: float | None
    us_30y: float | None
    spread_3m_10y: float | None
    curve_status: str  # NORMAL / INVERTED / FLAT / UNKNOWN
    as_of: str


def classify_curve(spread: float | None) -> str:
    """Classify yield curve from 3M-10Y spread."""
    if spread is None:
        return "UNKNOWN"
    if spread > 0.25:
        return "NORMAL"
    if spread < -0.25:
        return "INVERTED"
    return "FLAT"


def _fetch_yield(ticker: str) -> float | None:
    """Fetch latest yield from yfinance."""
    t = yf.Ticker(ticker)
    hist = t.history(period="5d")
    if hist.empty:
        return None
    return float(hist["Close"].iloc[-1])


def fetch_yield_curve() -> YieldCurve:
    """Fetch current Treasury yield curve."""
    yields: dict[str, float | None] = {}
    for name, ticker in _YIELD_TICKERS.items():
        yields[name] = _fetch_yield(ticker)

    us_3m = yields.get("us_3m")
    us_10y = yields.get("us_10y")
    spread = None
    if us_3m is not None and us_10y is not None:
        spread = us_10y - us_3m

    return YieldCurve(
        us_3m=us_3m,
        us_5y=yields.get("us_5y"),
        us_10y=us_10y,
        us_30y=yields.get("us_30y"),
        spread_3m_10y=spread,
        curve_status=classify_curve(spread),
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )

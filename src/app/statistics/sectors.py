from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import yfinance as yf


@dataclass(frozen=True, slots=True)
class SectorStrength:
    """Relative strength of one sector ETF."""

    ticker: str
    name: str
    price: float
    change_1d_pct: float
    change_5d_pct: float
    change_20d_pct: float
    relative_to_spy: float


@dataclass(frozen=True, slots=True)
class SectorRotation:
    """Sector rotation analysis."""

    leaders: tuple[SectorStrength, ...]
    laggards: tuple[SectorStrength, ...]
    rotation_signal: str
    as_of: str


SECTOR_ETFS: list[tuple[str, str]] = [
    ("XLK", "Technology"),
    ("XLF", "Financials"),
    ("XBI", "Biotech"),
    ("XLE", "Energy"),
    ("XLV", "Healthcare"),
    ("XLI", "Industrials"),
    ("XLU", "Utilities"),
]

_DEFENSIVE_SECTORS = {"XLU", "XLV"}
_GROWTH_SECTORS = {"XLK", "XBI"}


def calculate_sector_strength(
    ticker: str,
    name: str,
    spy_change_20d: float,
) -> SectorStrength | None:
    """Calculate strength for one sector ETF relative to SPY."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if len(hist) < 2:
            return None

        closes = hist["Close"]
        price = float(closes.iloc[-1])
        change_1d = (closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]
        idx_5 = min(5, len(closes) - 1)
        change_5d = (closes.iloc[-1] - closes.iloc[-idx_5]) / closes.iloc[-idx_5]
        change_20d = (closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]
        relative = float(change_20d) - spy_change_20d

        return SectorStrength(
            ticker=ticker,
            name=name,
            price=price,
            change_1d_pct=float(change_1d),
            change_5d_pct=float(change_5d),
            change_20d_pct=float(change_20d),
            relative_to_spy=relative,
        )
    except Exception:
        return None


def analyze_sector_rotation() -> SectorRotation:
    """Analyze sector rotation across all tracked sectors."""
    # Get SPY 20d change for relative calculation
    spy_change = 0.0
    try:
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="1mo")
        if len(spy_hist) >= 2:
            spy_close = spy_hist["Close"]
            spy_change = float(
                (spy_close.iloc[-1] - spy_close.iloc[0]) / spy_close.iloc[0],
            )
    except Exception:  # noqa: S110
        pass

    strengths: list[SectorStrength] = []
    for ticker, name in SECTOR_ETFS:
        s = calculate_sector_strength(ticker, name, spy_change)
        if s is not None:
            strengths.append(s)

    sorted_strengths = sorted(
        strengths,
        key=lambda s: s.relative_to_spy,
        reverse=True,
    )

    leaders = tuple(sorted_strengths[:3]) if sorted_strengths else ()
    laggards = tuple(sorted_strengths[-3:]) if sorted_strengths else ()

    # Classify rotation signal
    leader_tickers = {s.ticker for s in leaders}
    if leader_tickers & _DEFENSIVE_SECTORS:
        signal = "RISK_OFF"
    elif leader_tickers & _GROWTH_SECTORS:
        signal = "RISK_ON"
    else:
        signal = "NEUTRAL"

    return SectorRotation(
        leaders=leaders,
        laggards=laggards,
        rotation_signal=signal,
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )

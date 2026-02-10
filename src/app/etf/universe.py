from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ETFMapping:
    """Maps a leveraged ETF to its underlying index."""

    leveraged_ticker: str
    underlying_ticker: str
    name: str
    leverage: float
    drawdown_threshold: float
    alert_threshold: float
    profit_target: float


ETF_UNIVERSE: list[ETFMapping] = [
    ETFMapping("TQQQ", "QQQ", "Nasdaq-100 3x Bull", 3.0, 0.05, 0.03, 0.10),
    ETFMapping("UPRO", "SPY", "S&P 500 3x Bull", 3.0, 0.05, 0.03, 0.10),
    ETFMapping("SOXL", "SOXX", "Semiconductors 3x Bull", 3.0, 0.08, 0.05, 0.10),
    ETFMapping("TNA", "IWM", "Russell 2000 3x Bull", 3.0, 0.07, 0.04, 0.10),
    ETFMapping("TECL", "XLK", "Tech 3x Bull", 3.0, 0.07, 0.04, 0.10),
    ETFMapping("FAS", "XLF", "Financials 3x Bull", 3.0, 0.07, 0.04, 0.10),
    ETFMapping("LABU", "XBI", "Biotech 3x Bull", 3.0, 0.10, 0.07, 0.10),
    ETFMapping("UCO", "USO", "Oil 2x Bull", 2.0, 0.10, 0.07, 0.10),
]


def get_mapping(leveraged_ticker: str) -> ETFMapping | None:
    """Look up a mapping by leveraged ETF ticker."""
    for m in ETF_UNIVERSE:
        if m.leveraged_ticker == leveraged_ticker.upper():
            return m
    return None


def get_mapping_by_underlying(underlying_ticker: str) -> ETFMapping | None:
    """Look up a mapping by underlying index ticker."""
    for m in ETF_UNIVERSE:
        if m.underlying_ticker == underlying_ticker.upper():
            return m
    return None


def get_all_underlying_tickers() -> list[str]:
    """Return deduplicated list of all underlying tickers."""
    seen: set[str] = set()
    result: list[str] = []
    for m in ETF_UNIVERSE:
        if m.underlying_ticker not in seen:
            seen.add(m.underlying_ticker)
            result.append(m.underlying_ticker)
    return result

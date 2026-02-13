"""Portfolio exposure calculations."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.etf.universe import ETF_UNIVERSE

# Map leveraged tickers to sectors based on the ETF universe
_SECTOR_MAP: dict[str, str] = {}
for _m in ETF_UNIVERSE:
    _SECTOR_MAP[_m.leveraged_ticker] = _m.name.split()[0].lower()


def get_sector(leveraged_ticker: str) -> str:
    """Get the sector for a leveraged ETF ticker."""
    return _SECTOR_MAP.get(leveraged_ticker, "other")


@dataclass(frozen=True, slots=True)
class Position:
    """A portfolio position."""

    leveraged_ticker: str
    entry_price: float
    current_price: float
    shares: float
    leverage: int = 3

    @property
    def notional_value(self) -> float:
        """Current market value of the position."""
        return self.shares * self.current_price

    @property
    def leveraged_exposure(self) -> float:
        """Leveraged notional exposure."""
        return self.notional_value * self.leverage

    @property
    def unrealized_pl(self) -> float:
        """Unrealized P&L in dollars."""
        return self.shares * (self.current_price - self.entry_price)

    @property
    def unrealized_pl_pct(self) -> float:
        """Unrealized P&L as percentage."""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price

    @property
    def sector(self) -> str:
        """Sector classification."""
        return get_sector(self.leveraged_ticker)


@dataclass(frozen=True, slots=True)
class ExposureReport:
    """Portfolio exposure breakdown."""

    total_value: float
    invested_value: float
    cash_value: float
    invested_pct: float
    cash_pct: float
    total_leveraged_exposure: float
    leveraged_exposure_ratio: float
    sector_exposures: dict[str, float] = field(default_factory=dict)
    sector_pcts: dict[str, float] = field(default_factory=dict)
    position_count: int = 0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0


def calculate_exposure(
    positions: list[Position],
    portfolio_value: float,
) -> ExposureReport:
    """Calculate portfolio exposure from active positions."""
    invested = sum(p.notional_value for p in positions)
    cash = portfolio_value - invested
    invested_pct = invested / portfolio_value if portfolio_value > 0 else 0.0
    cash_pct = cash / portfolio_value if portfolio_value > 0 else 1.0

    total_leveraged = sum(p.leveraged_exposure for p in positions)
    leverage_ratio = total_leveraged / portfolio_value if portfolio_value > 0 else 0.0

    sector_exp: dict[str, float] = {}
    for p in positions:
        sector_exp[p.sector] = sector_exp.get(p.sector, 0.0) + p.notional_value

    sector_pcts = {
        s: v / portfolio_value if portfolio_value > 0 else 0.0
        for s, v in sector_exp.items()
    }

    unrealized = sum(p.unrealized_pl for p in positions)
    unrealized_pct = unrealized / portfolio_value if portfolio_value > 0 else 0.0

    return ExposureReport(
        total_value=portfolio_value,
        invested_value=invested,
        cash_value=cash,
        invested_pct=invested_pct,
        cash_pct=cash_pct,
        total_leveraged_exposure=total_leveraged,
        leveraged_exposure_ratio=leverage_ratio,
        sector_exposures=sector_exp,
        sector_pcts=sector_pcts,
        position_count=len(positions),
        unrealized_pl=unrealized,
        unrealized_pl_pct=unrealized_pct,
    )

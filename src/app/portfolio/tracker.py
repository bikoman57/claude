"""Portfolio tracking — aggregate positions, cash, allocations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_PORTFOLIO_PATH = Path("data/portfolio.json")
_DEFAULT_VALUE = 10_000.0


@dataclass
class PortfolioConfig:
    """Persisted portfolio configuration."""

    total_value: float = _DEFAULT_VALUE
    cash_balance: float = _DEFAULT_VALUE

    def save(self) -> None:
        """Save portfolio config to JSON."""
        _PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PORTFOLIO_PATH.write_text(
            json.dumps(
                {
                    "total_value": self.total_value,
                    "cash_balance": self.cash_balance,
                },
                indent=2,
            )
        )

    @classmethod
    def load(cls) -> PortfolioConfig:
        """Load portfolio config from JSON or return defaults."""
        if _PORTFOLIO_PATH.exists():
            data = json.loads(_PORTFOLIO_PATH.read_text())
            return cls(
                total_value=float(data.get("total_value", _DEFAULT_VALUE)),
                cash_balance=float(data.get("cash_balance", _DEFAULT_VALUE)),
            )
        return cls()


@dataclass(frozen=True, slots=True)
class AllocationEntry:
    """One entry in the allocation breakdown."""

    ticker: str
    sector: str
    value: float
    pct: float


@dataclass(frozen=True, slots=True)
class PortfolioDashboard:
    """Snapshot of portfolio state."""

    total_value: float
    invested_value: float
    cash_value: float
    invested_pct: float
    cash_pct: float
    position_count: int
    unrealized_pl: float
    unrealized_pl_pct: float
    allocations: list[AllocationEntry] = field(default_factory=list)

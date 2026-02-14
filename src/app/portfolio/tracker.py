"""Portfolio tracking — aggregate positions, cash, allocations, snapshots."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PORTFOLIO_PATH = Path("data/portfolio.json")
_HISTORY_PATH = Path("data/portfolio_history.json")
_DEFAULT_VALUE = 10_000.0
_DEFAULT_MONTHLY_COST = 100.0


@dataclass
class PortfolioPosition:
    """An open position in the portfolio."""

    ticker: str
    underlying: str
    shares: float
    entry_price: float
    entry_date: str


@dataclass
class PortfolioConfig:
    """Persisted portfolio configuration."""

    total_value: float = _DEFAULT_VALUE
    cash_balance: float = _DEFAULT_VALUE
    positions: list[PortfolioPosition] = field(default_factory=list)
    realized_pl: float = 0.0
    total_operating_costs: float = 0.0
    last_cost_date: str = ""

    def save(self) -> None:
        """Save portfolio config to JSON."""
        _PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PORTFOLIO_PATH.write_text(
            json.dumps(
                {
                    "total_value": self.total_value,
                    "cash_balance": self.cash_balance,
                    "positions": [asdict(p) for p in self.positions],
                    "realized_pl": self.realized_pl,
                    "total_operating_costs": self.total_operating_costs,
                    "last_cost_date": self.last_cost_date,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> PortfolioConfig:
        """Load portfolio config from JSON or return defaults."""
        if _PORTFOLIO_PATH.exists():
            data = json.loads(_PORTFOLIO_PATH.read_text(encoding="utf-8"))
            positions = [
                PortfolioPosition(**p) for p in data.get("positions", [])
            ]
            return cls(
                total_value=float(data.get("total_value", _DEFAULT_VALUE)),
                cash_balance=float(data.get("cash_balance", _DEFAULT_VALUE)),
                positions=positions,
                realized_pl=float(data.get("realized_pl", 0.0)),
                total_operating_costs=float(
                    data.get("total_operating_costs", 0.0)
                ),
                last_cost_date=data.get("last_cost_date", ""),
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


# ---------------------------------------------------------------------------
# Portfolio update operations
# ---------------------------------------------------------------------------


def enter_position(
    config: PortfolioConfig,
    ticker: str,
    underlying: str,
    entry_price: float,
    position_value: float,
) -> PortfolioConfig:
    """Enter a new position: deduct from cash, add to positions."""
    if position_value > config.cash_balance:
        position_value = config.cash_balance * 0.95  # cap at 95% of cash

    shares = position_value / entry_price if entry_price > 0 else 0.0
    config.positions.append(
        PortfolioPosition(
            ticker=ticker,
            underlying=underlying,
            shares=shares,
            entry_price=entry_price,
            entry_date=datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        )
    )
    config.cash_balance -= position_value
    config.total_value = config.cash_balance + sum(
        p.shares * p.entry_price for p in config.positions
    )
    config.save()
    return config


def close_position(
    config: PortfolioConfig,
    ticker: str,
    exit_price: float,
) -> tuple[PortfolioConfig, float]:
    """Close a position: realize P&L, add proceeds to cash.

    Returns (updated_config, pl_pct).
    """
    pos = next(
        (p for p in config.positions if p.ticker == ticker.upper()), None
    )
    if pos is None:
        return config, 0.0

    exit_value = pos.shares * exit_price
    cost_basis = pos.shares * pos.entry_price
    pl = exit_value - cost_basis
    pl_pct = pl / cost_basis if cost_basis > 0 else 0.0

    config.cash_balance += exit_value
    config.realized_pl += pl
    config.positions = [p for p in config.positions if p.ticker != ticker.upper()]
    config.total_value = config.cash_balance + sum(
        p.shares * p.entry_price for p in config.positions
    )
    config.save()
    return config, pl_pct


def apply_operating_costs(
    config: PortfolioConfig,
    monthly_cost: float = _DEFAULT_MONTHLY_COST,
) -> PortfolioConfig:
    """Apply proportional operating costs since last cost date."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    if config.last_cost_date == today:
        return config  # already applied today

    if not config.last_cost_date:
        # First run — just set the date, don't charge
        config.last_cost_date = today
        config.save()
        return config

    last = datetime.strptime(config.last_cost_date, "%Y-%m-%d").replace(
        tzinfo=UTC
    )
    now = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=UTC)
    days = (now - last).days
    if days <= 0:
        return config

    daily_cost = monthly_cost / 30.0
    cost = daily_cost * days
    config.cash_balance -= cost
    config.total_operating_costs += cost
    config.last_cost_date = today
    config.total_value = config.cash_balance + sum(
        p.shares * p.entry_price for p in config.positions
    )
    config.save()
    return config


def compute_total_value(
    config: PortfolioConfig,
    current_prices: dict[str, float] | None = None,
) -> float:
    """Compute total portfolio value with optional live prices."""
    invested = 0.0
    for pos in config.positions:
        price = (
            current_prices.get(pos.ticker, pos.entry_price)
            if current_prices
            else pos.entry_price
        )
        invested += pos.shares * price
    return config.cash_balance + invested


# ---------------------------------------------------------------------------
# Snapshot system
# ---------------------------------------------------------------------------


@dataclass
class PortfolioSnapshot:
    """A point-in-time portfolio snapshot for history tracking."""

    date: str
    total_value: float
    cash_balance: float
    invested_value: float
    unrealized_pl: float
    realized_pl_cumulative: float
    operating_costs_cumulative: float
    net_value: float
    position_count: int
    positions_summary: list[dict[str, object]] = field(default_factory=list)


def save_snapshot(snapshot: PortfolioSnapshot) -> None:
    """Append a snapshot to the history file."""
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, object]] = []
    if _HISTORY_PATH.exists():
        history = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))

    # Replace existing snapshot for same date
    history = [s for s in history if s.get("date") != snapshot.date]
    history.append(asdict(snapshot))
    history.sort(key=lambda s: str(s.get("date", "")))

    _HISTORY_PATH.write_text(
        json.dumps(history, indent=2), encoding="utf-8"
    )


def load_history() -> list[PortfolioSnapshot]:
    """Load all snapshots from history file, sorted chronologically."""
    if not _HISTORY_PATH.exists():
        return []
    raw: list[dict[str, Any]] = json.loads(
        _HISTORY_PATH.read_text(encoding="utf-8")
    )
    snapshots = []
    for item in raw:
        snapshots.append(
            PortfolioSnapshot(
                date=str(item.get("date", "")),
                total_value=float(item.get("total_value", 0)),
                cash_balance=float(item.get("cash_balance", 0)),
                invested_value=float(item.get("invested_value", 0)),
                unrealized_pl=float(item.get("unrealized_pl", 0)),
                realized_pl_cumulative=float(
                    item.get("realized_pl_cumulative", 0)
                ),
                operating_costs_cumulative=float(
                    item.get("operating_costs_cumulative", 0)
                ),
                net_value=float(item.get("net_value", 0)),
                position_count=int(item.get("position_count", 0)),
                positions_summary=list(item.get("positions_summary", [])),
            )
        )
    return snapshots


def take_snapshot(config: PortfolioConfig) -> PortfolioSnapshot:
    """Create a snapshot from current portfolio state."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    invested = sum(p.shares * p.entry_price for p in config.positions)
    unrealized = 0.0  # Would need current prices for accurate unrealized P&L

    positions_summary = [
        {
            "ticker": p.ticker,
            "shares": round(p.shares, 4),
            "entry_price": p.entry_price,
            "value": round(p.shares * p.entry_price, 2),
        }
        for p in config.positions
    ]

    total = config.cash_balance + invested
    net = total - config.total_operating_costs

    snapshot = PortfolioSnapshot(
        date=today,
        total_value=round(total, 2),
        cash_balance=round(config.cash_balance, 2),
        invested_value=round(invested, 2),
        unrealized_pl=round(unrealized, 2),
        realized_pl_cumulative=round(config.realized_pl, 2),
        operating_costs_cumulative=round(config.total_operating_costs, 2),
        net_value=round(net, 2),
        position_count=len(config.positions),
        positions_summary=positions_summary,
    )
    save_snapshot(snapshot)
    return snapshot

"""Portfolio management CLI."""

from __future__ import annotations

import sys

from app.etf.store import get_active_signals
from app.portfolio.sizing import fixed_fraction_size, kelly_size
from app.portfolio.tracker import (
    PortfolioConfig,
    apply_operating_costs,
    load_history,
    take_snapshot,
)
from app.risk.exposure import Position, calculate_exposure, get_sector

USAGE = """\
Usage:
  uv run python -m app.portfolio dashboard     Portfolio overview
  uv run python -m app.portfolio allocations    Sector allocations
  uv run python -m app.portfolio sizing         Position sizing recommendations
  uv run python -m app.portfolio history        Portfolio value history
  uv run python -m app.portfolio snapshot       Save daily portfolio snapshot
"""


def _build_positions(config: PortfolioConfig) -> list[Position]:
    """Build position list from active signals and portfolio positions."""
    # First try portfolio positions (preferred — has actual shares)
    positions: list[Position] = []
    for pos in config.positions:
        positions.append(
            Position(
                leveraged_ticker=pos.ticker,
                entry_price=pos.entry_price,
                current_price=pos.entry_price,  # use entry as proxy
                shares=pos.shares,
            )
        )

    if positions:
        return positions

    # Fallback: estimate from active signals (legacy behavior)
    signals = get_active_signals()
    for sig in signals:
        if sig.leveraged_entry_price and sig.leveraged_current_price:
            est_value = config.total_value * 0.15
            shares = est_value / sig.leveraged_entry_price
            positions.append(
                Position(
                    leveraged_ticker=sig.leveraged_ticker,
                    entry_price=sig.leveraged_entry_price,
                    current_price=sig.leveraged_current_price,
                    shares=shares,
                )
            )
    return positions


def cmd_dashboard() -> int:
    """Show portfolio dashboard."""
    config = PortfolioConfig.load()
    positions = _build_positions(config)
    report = calculate_exposure(positions, config.total_value)

    print("=== PORTFOLIO DASHBOARD ===")  # noqa: T201
    print(f"Total value: ${report.total_value:,.0f}")  # noqa: T201
    print(  # noqa: T201
        f"Invested: ${report.invested_value:,.0f} ({report.invested_pct:.0%})"
        f" | Cash: ${report.cash_value:,.0f} ({report.cash_pct:.0%})"
    )
    print(f"Positions: {report.position_count}")  # noqa: T201
    print(  # noqa: T201
        f"Unrealized P/L: ${report.unrealized_pl:+,.0f}"
        f" ({report.unrealized_pl_pct:+.1%})"
    )
    print(f"Realized P/L: ${config.realized_pl:+,.2f}")  # noqa: T201
    print(f"Operating costs: ${config.total_operating_costs:,.2f}")  # noqa: T201
    net = config.total_value - config.total_operating_costs
    print(f"Net value (after costs): ${net:,.2f}")  # noqa: T201
    return 0


def cmd_allocations() -> int:
    """Show sector allocations."""
    config = PortfolioConfig.load()
    positions = _build_positions(config)
    report = calculate_exposure(positions, config.total_value)

    print("=== SECTOR ALLOCATIONS ===")  # noqa: T201
    if not positions:
        print("No active positions.")  # noqa: T201
        return 0

    for sector, pct in sorted(
        report.sector_pcts.items(), key=lambda x: x[1], reverse=True
    ):
        val = report.sector_exposures[sector]
        tickers = [
            p.leveraged_ticker
            for p in positions
            if get_sector(p.leveraged_ticker) == sector
        ]
        print(f"  {sector}: ${val:,.0f} ({pct:.0%}) — {', '.join(tickers)}")  # noqa: T201

    print(f"\n  Cash: ${report.cash_value:,.0f} ({report.cash_pct:.0%})")  # noqa: T201
    return 0


def cmd_sizing() -> int:
    """Show position sizing recommendations."""
    config = PortfolioConfig.load()

    print("=== POSITION SIZING ===")  # noqa: T201
    print(f"Portfolio: ${config.total_value:,.0f}\n")  # noqa: T201

    # Fixed-fraction sizing
    ff = fixed_fraction_size(config.total_value, risk_pct=0.02, leverage=3)
    print("Fixed-Fraction (2% risk, 3x leverage):")  # noqa: T201
    print(f"  Position: ${ff.position_value:,.0f} ({ff.portfolio_pct:.0%})")  # noqa: T201
    print(f"  {ff.rationale}\n")  # noqa: T201

    # Kelly sizing (with example parameters)
    k = kelly_size(
        config.total_value,
        win_rate=0.65,
        avg_win=0.10,
        avg_loss=0.08,
        fraction=0.5,
    )
    print("Half-Kelly (65% win rate, 10% avg win, 8% avg loss):")  # noqa: T201
    print(f"  Position: ${k.position_value:,.0f} ({k.portfolio_pct:.0%})")  # noqa: T201
    print(f"  {k.rationale}")  # noqa: T201
    return 0


def cmd_snapshot() -> int:
    """Save a daily portfolio snapshot."""
    config = PortfolioConfig.load()
    config = apply_operating_costs(config)
    snapshot = take_snapshot(config)

    print("=== PORTFOLIO SNAPSHOT ===")  # noqa: T201
    print(f"Date: {snapshot.date}")  # noqa: T201
    print(f"Total value: ${snapshot.total_value:,.2f}")  # noqa: T201
    print(f"Cash: ${snapshot.cash_balance:,.2f}")  # noqa: T201
    print(f"Invested: ${snapshot.invested_value:,.2f}")  # noqa: T201
    print(f"Realized P/L: ${snapshot.realized_pl_cumulative:+,.2f}")  # noqa: T201
    print(f"Operating costs: ${snapshot.operating_costs_cumulative:,.2f}")  # noqa: T201
    print(f"Net value: ${snapshot.net_value:,.2f}")  # noqa: T201
    print(f"Positions: {snapshot.position_count}")  # noqa: T201
    print("Snapshot saved.")  # noqa: T201
    return 0


def cmd_history() -> int:
    """Show portfolio value history."""
    print("=== PORTFOLIO HISTORY ===")  # noqa: T201
    history = load_history()
    if not history:
        print("No history snapshots yet. Run 'snapshot' to start tracking.")  # noqa: T201
        return 0

    print(  # noqa: T201
        f"{'Date':<12} {'Value':>10} {'Cash':>10} {'Invested':>10}"
        f" {'Real P/L':>10} {'Costs':>8} {'Net':>10}"
    )
    print("-" * 72)  # noqa: T201
    for s in history:
        print(  # noqa: T201
            f"{s.date:<12} ${s.total_value:>9,.2f} ${s.cash_balance:>9,.2f}"
            f" ${s.invested_value:>9,.2f} ${s.realized_pl_cumulative:>+9,.2f}"
            f" ${s.operating_costs_cumulative:>7,.2f} ${s.net_value:>9,.2f}"
        )
    return 0


def main() -> int:
    """CLI entry point."""
    args = sys.argv[1:]
    if not args:
        print(USAGE)  # noqa: T201
        return 1

    commands = {
        "dashboard": cmd_dashboard,
        "allocations": cmd_allocations,
        "sizing": cmd_sizing,
        "history": cmd_history,
        "snapshot": cmd_snapshot,
    }

    cmd = args[0]
    if cmd not in commands:
        print(f"Unknown command: {cmd}")  # noqa: T201
        print(USAGE)  # noqa: T201
        return 1

    return commands[cmd]()


if __name__ == "__main__":
    raise SystemExit(main())

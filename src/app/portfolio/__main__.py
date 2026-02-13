"""Portfolio management CLI."""

from __future__ import annotations

import sys

from app.etf.store import get_active_signals
from app.portfolio.sizing import fixed_fraction_size, kelly_size
from app.portfolio.tracker import PortfolioConfig
from app.risk.exposure import Position, calculate_exposure, get_sector

USAGE = """\
Usage:
  uv run python -m app.portfolio dashboard     Portfolio overview
  uv run python -m app.portfolio allocations    Sector allocations
  uv run python -m app.portfolio sizing         Position sizing recommendations
  uv run python -m app.portfolio history        Portfolio value history
"""


def _build_positions(config: PortfolioConfig) -> list[Position]:
    """Build position list from active signals."""
    signals = get_active_signals()
    positions: list[Position] = []
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


def cmd_history() -> int:
    """Show portfolio value history."""
    print("=== PORTFOLIO HISTORY ===")  # noqa: T201
    print("No history snapshots yet. Run daily to build history.")  # noqa: T201
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
    }

    cmd = args[0]
    if cmd not in commands:
        print(f"Unknown command: {cmd}")  # noqa: T201
        print(USAGE)  # noqa: T201
        return 1

    return commands[cmd]()


if __name__ == "__main__":
    raise SystemExit(main())

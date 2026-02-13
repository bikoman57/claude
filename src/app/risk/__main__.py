"""Risk management CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.etf.store import get_active_signals
from app.risk.exposure import ExposureReport, Position, calculate_exposure
from app.risk.limits import DEFAULT_LIMITS

USAGE = """\
Usage:
  uv run python -m app.risk dashboard    Full risk dashboard
  uv run python -m app.risk check        Check current exposure
  uv run python -m app.risk limits       Show risk limits
"""

_PORTFOLIO_PATH = Path("data/portfolio.json")
_DEFAULT_PORTFOLIO_VALUE = 10_000.0


def _load_portfolio_value() -> float:
    """Load portfolio value from config or use default."""
    if _PORTFOLIO_PATH.exists():
        data = json.loads(_PORTFOLIO_PATH.read_text())
        return float(data.get("total_value", _DEFAULT_PORTFOLIO_VALUE))
    return _DEFAULT_PORTFOLIO_VALUE


def _build_positions() -> list[Position]:
    """Build position list from active signals."""
    signals = get_active_signals()
    positions: list[Position] = []
    for sig in signals:
        if sig.leveraged_entry_price and sig.leveraged_current_price:
            # Estimate shares from a default position size
            portfolio_val = _load_portfolio_value()
            est_position_value = portfolio_val * 0.15  # ~15% per position
            shares = est_position_value / sig.leveraged_entry_price
            positions.append(
                Position(
                    leveraged_ticker=sig.leveraged_ticker,
                    entry_price=sig.leveraged_entry_price,
                    current_price=sig.leveraged_current_price,
                    shares=shares,
                )
            )
    return positions


def _format_exposure(report: ExposureReport) -> str:
    """Format exposure report for display."""
    lines = [
        "=== RISK DASHBOARD ===",
        f"Portfolio: ${report.total_value:,.0f}",
        f"Invested: ${report.invested_value:,.0f} ({report.invested_pct:.0%})"
        f" | Cash: ${report.cash_value:,.0f} ({report.cash_pct:.0%})",
        f"Positions: {report.position_count}"
        f"/{DEFAULT_LIMITS.max_concurrent_positions}",
        f"Leveraged exposure: ${report.total_leveraged_exposure:,.0f}"
        f" ({report.leveraged_exposure_ratio:.1f}x)",
        f"Unrealized P/L: ${report.unrealized_pl:+,.0f}"
        f" ({report.unrealized_pl_pct:+.1%})",
        "",
        "SECTOR ALLOCATION:",
    ]

    if report.sector_pcts:
        for sector, pct in sorted(
            report.sector_pcts.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            val = report.sector_exposures[sector]
            status = (
                "WARNING"
                if pct > DEFAULT_LIMITS.max_sector_exposure_pct * 0.8
                else "OK"
            )
            lines.append(f"  {sector}: ${val:,.0f} ({pct:.0%}) [{status}]")
    else:
        lines.append("  No positions")

    # Risk status
    lines.append("")
    warnings: list[str] = []
    if report.position_count >= DEFAULT_LIMITS.max_concurrent_positions:
        warnings.append("Max positions reached")
    if report.cash_pct < DEFAULT_LIMITS.min_cash_reserve_pct:
        warnings.append(f"Cash below minimum ({report.cash_pct:.0%})")
    if report.leveraged_exposure_ratio > DEFAULT_LIMITS.max_total_leveraged_exposure:
        warnings.append(
            f"Leverage exceeds limit ({report.leveraged_exposure_ratio:.1f}x)"
        )
    for sector, pct in report.sector_pcts.items():
        if pct > DEFAULT_LIMITS.max_sector_exposure_pct:
            warnings.append(f"Sector {sector} over limit ({pct:.0%})")

    if warnings:
        lines.append(f"RISK STATUS: WARNING — {'; '.join(warnings)}")
    else:
        lines.append("RISK STATUS: WITHIN LIMITS")

    return "\n".join(lines)


def cmd_dashboard() -> int:
    """Show full risk dashboard."""
    positions = _build_positions()
    portfolio_val = _load_portfolio_value()
    report = calculate_exposure(positions, portfolio_val)
    print(_format_exposure(report))  # noqa: T201
    return 0


def cmd_check() -> int:
    """Check current exposure against limits."""
    positions = _build_positions()
    portfolio_val = _load_portfolio_value()
    report = calculate_exposure(positions, portfolio_val)

    max_pos = DEFAULT_LIMITS.max_concurrent_positions
    min_cash = DEFAULT_LIMITS.min_cash_reserve_pct
    max_lev = DEFAULT_LIMITS.max_total_leveraged_exposure
    print(f"Positions: {report.position_count}/{max_pos}")  # noqa: T201
    print(f"Cash: {report.cash_pct:.0%} (min {min_cash:.0%})")  # noqa: T201
    print(f"Leverage: {report.leveraged_exposure_ratio:.1f}x (max {max_lev}x)")  # noqa: T201

    for sector, pct in report.sector_pcts.items():
        status = "OVER" if pct > DEFAULT_LIMITS.max_sector_exposure_pct else "ok"
        print(f"  {sector}: {pct:.0%} [{status}]")  # noqa: T201

    return 0


def cmd_limits() -> int:
    """Show current risk limits."""
    lim = DEFAULT_LIMITS
    print("=== RISK LIMITS ===")  # noqa: T201
    print(f"Max concurrent positions: {lim.max_concurrent_positions}")  # noqa: T201
    print(f"Max single position: {lim.max_single_position_pct:.0%}")  # noqa: T201
    print(f"Max sector exposure: {lim.max_sector_exposure_pct:.0%}")  # noqa: T201
    print(f"Max leveraged exposure: {lim.max_total_leveraged_exposure}x")  # noqa: T201
    print(f"Min cash reserve: {lim.min_cash_reserve_pct:.0%}")  # noqa: T201
    return 0


def main() -> int:
    """CLI entry point."""
    args = sys.argv[1:]
    if not args:
        print(USAGE)  # noqa: T201
        return 1

    commands = {
        "dashboard": cmd_dashboard,
        "check": cmd_check,
        "limits": cmd_limits,
    }

    cmd = args[0]
    if cmd not in commands:
        print(f"Unknown command: {cmd}")  # noqa: T201
        print(USAGE)  # noqa: T201
        return 1

    return commands[cmd]()


if __name__ == "__main__":
    raise SystemExit(main())

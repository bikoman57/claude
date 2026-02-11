"""Strategy analyst CLI.

Usage:
    python -m app.strategy backtest <ticker> [--threshold X] [--target Y] [--period Zy]
    python -m app.strategy optimize <ticker>
    python -m app.strategy proposals
    python -m app.strategy compare <ticker>
    python -m app.strategy history [<ticker>]
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict

from app.etf.universe import get_mapping_by_underlying
from app.strategy.backtest import BacktestConfig, run_backtest
from app.strategy.proposals import generate_proposals, optimize_single_etf
from app.strategy.store import list_backtests, load_backtest, save_backtest


def _parse_float_arg(args: list[str], flag: str, default: float) -> float:
    """Extract a --flag value from args."""
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return float(args[i + 1])
    return default


def _cmd_backtest(args: list[str]) -> int:
    if len(args) < 1:
        print(  # noqa: T201
            "Usage: backtest <underlying_ticker>"
            " [--threshold X] [--target Y] [--period Zy]",
        )
        return 1

    ticker = args[0].upper()
    mapping = get_mapping_by_underlying(ticker)
    leverage = mapping.leverage if mapping else 3.0
    threshold = _parse_float_arg(args, "--threshold", 0.05)
    target = _parse_float_arg(args, "--target", 0.10)
    stop = _parse_float_arg(args, "--stop", 0.15)

    period = "2y"
    for i, a in enumerate(args):
        if a == "--period" and i + 1 < len(args):
            period = args[i + 1]

    config = BacktestConfig(
        underlying_ticker=ticker,
        leverage=leverage,
        entry_threshold=threshold,
        profit_target=target,
        stop_loss=stop,
        period=period,
    )

    result = run_backtest(config)
    if result is None:
        print(f"No data for {ticker}")  # noqa: T201
        return 1

    path = save_backtest(result)
    print(json.dumps(asdict(result), indent=2))  # noqa: T201
    print(f"\nSaved to {path}")  # noqa: T201
    return 0


def _cmd_optimize(args: list[str]) -> int:
    if len(args) < 1:
        print("Usage: optimize <underlying_ticker>")  # noqa: T201
        return 1

    ticker = args[0].upper()
    mapping = get_mapping_by_underlying(ticker)
    if mapping is None:
        print(f"Unknown ticker: {ticker}")  # noqa: T201
        return 1

    breakdown = optimize_single_etf(mapping)
    output = {
        "ticker": mapping.leveraged_ticker,
        "underlying": mapping.underlying_ticker,
        "results_tested": len(breakdown.results),
        "best_threshold": breakdown.best_threshold,
        "best_target": breakdown.best_target,
    }
    if breakdown.best_result is not None:
        output["best_sharpe"] = breakdown.best_result.sharpe_ratio
        output["best_win_rate"] = breakdown.best_result.win_rate
        output["best_total_return"] = breakdown.best_result.total_return
        output["trades"] = len(breakdown.best_result.trades)

    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def _cmd_proposals() -> int:
    summary = generate_proposals()
    print(  # noqa: T201
        json.dumps(
            [asdict(p) for p in summary.proposals],
            indent=2,
        )
    )
    return 0


def _cmd_compare(args: list[str]) -> int:
    if len(args) < 1:
        print("Usage: compare <underlying_ticker>")  # noqa: T201
        return 1

    ticker = args[0].upper()
    mapping = get_mapping_by_underlying(ticker)
    if mapping is None:
        print(f"Unknown ticker: {ticker}")  # noqa: T201
        return 1

    breakdown = optimize_single_etf(mapping)
    rows = []
    for r in breakdown.results:
        rows.append(
            {
                "threshold": r.config.entry_threshold,
                "target": r.config.profit_target,
                "trades": len(r.trades),
                "total_return": round(r.total_return, 4),
                "sharpe": (
                    round(r.sharpe_ratio, 3) if r.sharpe_ratio is not None else None
                ),
                "win_rate": (round(r.win_rate, 3) if r.win_rate is not None else None),
                "max_drawdown": round(r.max_drawdown, 4),
            }
        )

    rows.sort(
        key=lambda x: x["sharpe"] if x["sharpe"] is not None else -999,
        reverse=True,
    )
    print(json.dumps(rows, indent=2))  # noqa: T201
    return 0


def _cmd_history(args: list[str]) -> int:
    ticker = args[0].upper() if args else None
    files = list_backtests(ticker)
    if not files:
        print("No saved backtests found.")  # noqa: T201
        return 0

    for f in files:
        result = load_backtest(f)
        cfg = result.config
        sharpe = (
            f"{result.sharpe_ratio:.3f}" if result.sharpe_ratio is not None else "N/A"
        )
        wr = f"{result.win_rate:.1%}" if result.win_rate is not None else "N/A"
        print(  # noqa: T201
            f"{f.name}: {cfg.underlying_ticker} "
            f"threshold={cfg.entry_threshold:.0%} "
            f"target={cfg.profit_target:.0%} "
            f"trades={len(result.trades)} "
            f"return={result.total_return:.2%} "
            f"sharpe={sharpe} win_rate={wr}",
        )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        return 1

    cmd = sys.argv[1]
    args = sys.argv[2:]

    match cmd:
        case "backtest":
            return _cmd_backtest(args)
        case "optimize":
            return _cmd_optimize(args)
        case "proposals":
            return _cmd_proposals()
        case "compare":
            return _cmd_compare(args)
        case "history":
            return _cmd_history(args)
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Strategy analyst CLI.

Usage:
    python -m app.strategy backtest <ticker> [options]
    python -m app.strategy optimize <ticker>
    python -m app.strategy proposals
    python -m app.strategy compare <ticker>
    python -m app.strategy history [<ticker>]
    python -m app.strategy backtest-all [--period Zy]
    python -m app.strategy strategies
    python -m app.strategy forecast
    python -m app.strategy verify

Strategy types: ath_mean_reversion, rsi_oversold, bollinger_lower, ma_dip
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from app.etf.universe import ETF_UNIVERSE, get_mapping_by_underlying
from app.strategy.backtest import (
    STRATEGY_DESCRIPTIONS,
    THRESHOLD_LABELS,
    BacktestConfig,
    StrategyType,
    run_backtest,
)
from app.strategy.proposals import generate_proposals, optimize_single_etf
from app.strategy.store import list_backtests, load_backtest, save_backtest


def _parse_float_arg(args: list[str], flag: str, default: float) -> float:
    """Extract a --flag value from args."""
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return float(args[i + 1])
    return default


def _parse_str_arg(args: list[str], flag: str, default: str) -> str:
    """Extract a string --flag value from args."""
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
    return default


def _cmd_backtest(args: list[str]) -> int:
    if len(args) < 1:
        print(  # noqa: T201
            "Usage: backtest <underlying_ticker>"
            " [--strategy TYPE] [--threshold X] [--target Y] [--period Zy]",
        )
        return 1

    ticker = args[0].upper()
    mapping = get_mapping_by_underlying(ticker)
    leverage = mapping.leverage if mapping else 3.0
    threshold = _parse_float_arg(args, "--threshold", 0.05)
    target = _parse_float_arg(args, "--target", 0.10)
    stop = _parse_float_arg(args, "--stop", 0.15)
    period = _parse_str_arg(args, "--period", "2y")
    strategy = _parse_str_arg(
        args,
        "--strategy",
        StrategyType.ATH_MEAN_REVERSION,
    )

    config = BacktestConfig(
        underlying_ticker=ticker,
        leverage=leverage,
        entry_threshold=threshold,
        profit_target=target,
        stop_loss=stop,
        period=period,
        strategy_type=strategy,
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
    output: dict[str, object] = {
        "ticker": mapping.leveraged_ticker,
        "underlying": mapping.underlying_ticker,
        "results_tested": len(breakdown.results),
        "best_strategy": breakdown.best_strategy_type,
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
    rows: list[dict[str, float | str | int | None]] = []
    for r in breakdown.results:
        rows.append(
            {
                "strategy": r.config.strategy_type,
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
        key=lambda x: float(x["sharpe"]) if x["sharpe"] is not None else -999.0,
        reverse=True,
    )
    print(json.dumps(rows, indent=2))  # noqa: T201
    return 0


def _cmd_backtest_all(args: list[str]) -> int:
    """Run backtests for all ETFs across all strategies."""
    period = _parse_str_arg(args, "--period", "2y")

    results: list[dict[str, object]] = []
    for mapping in ETF_UNIVERSE:
        for stype in StrategyType:
            config = BacktestConfig(
                underlying_ticker=mapping.underlying_ticker,
                leverage=mapping.leverage,
                entry_threshold=mapping.drawdown_threshold,
                profit_target=mapping.profit_target,
                stop_loss=0.15,
                period=period,
                strategy_type=stype,
            )
            # Use strategy-appropriate defaults for non-ATH strategies
            if stype == StrategyType.RSI_OVERSOLD:
                config = BacktestConfig(
                    underlying_ticker=mapping.underlying_ticker,
                    leverage=mapping.leverage,
                    entry_threshold=30.0,
                    profit_target=mapping.profit_target,
                    stop_loss=0.15,
                    period=period,
                    strategy_type=stype,
                )
            elif stype == StrategyType.BOLLINGER_LOWER:
                config = BacktestConfig(
                    underlying_ticker=mapping.underlying_ticker,
                    leverage=mapping.leverage,
                    entry_threshold=2.0,
                    profit_target=mapping.profit_target,
                    stop_loss=0.15,
                    period=period,
                    strategy_type=stype,
                )
            elif stype == StrategyType.MA_DIP:
                config = BacktestConfig(
                    underlying_ticker=mapping.underlying_ticker,
                    leverage=mapping.leverage,
                    entry_threshold=0.03,
                    profit_target=mapping.profit_target,
                    stop_loss=0.15,
                    period=period,
                    strategy_type=stype,
                )

            result = run_backtest(config)
            if result is None:
                continue

            # Build equity curve from trades
            equity: list[float] = [10000.0]
            for trade in result.trades:
                equity.append(equity[-1] * (1 + trade.leveraged_return))

            trades_data = [
                {
                    "entry_day": t.entry_day,
                    "exit_day": t.exit_day,
                    "entry_date": t.entry_date,
                    "exit_date": t.exit_date,
                    "entry_price": round(t.entry_price, 2),
                    "exit_price": round(t.exit_price, 2),
                    "drawdown_at_entry": round(t.drawdown_at_entry, 4),
                    "leveraged_return": round(t.leveraged_return, 4),
                    "exit_reason": t.exit_reason,
                }
                for t in result.trades
            ]

            results.append(
                {
                    "leveraged_ticker": mapping.leveraged_ticker,
                    "underlying_ticker": mapping.underlying_ticker,
                    "strategy_type": str(stype),
                    "leverage": mapping.leverage,
                    "entry_threshold": config.entry_threshold,
                    "profit_target": config.profit_target,
                    "period": period,
                    "total_days": result.total_days,
                    "total_return": round(result.total_return, 4),
                    "sharpe_ratio": (
                        round(result.sharpe_ratio, 3)
                        if result.sharpe_ratio is not None
                        else None
                    ),
                    "win_rate": (
                        round(result.win_rate, 3)
                        if result.win_rate is not None
                        else None
                    ),
                    "max_drawdown": round(result.max_drawdown, 4),
                    "avg_gain": (
                        round(result.avg_gain, 4)
                        if result.avg_gain is not None
                        else None
                    ),
                    "avg_loss": (
                        round(result.avg_loss, 4)
                        if result.avg_loss is not None
                        else None
                    ),
                    "trade_count": len(result.trades),
                    "trades": trades_data,
                    "equity_curve": [round(e, 2) for e in equity],
                }
            )

    print(json.dumps(results, indent=2))  # noqa: T201
    return 0


def _cmd_strategies() -> int:
    """List all supported strategy types."""
    output = []
    for stype in StrategyType:
        output.append(
            {
                "type": str(stype),
                "description": STRATEGY_DESCRIPTIONS.get(stype, ""),
                "threshold_label": THRESHOLD_LABELS.get(stype, ""),
            }
        )
    print(json.dumps(output, indent=2))  # noqa: T201
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
        strategy = getattr(cfg, "strategy_type", "ath_mean_reversion")
        print(  # noqa: T201
            f"{f.name}: {cfg.underlying_ticker} "
            f"strategy={strategy} "
            f"threshold={cfg.entry_threshold} "
            f"target={cfg.profit_target:.0%} "
            f"trades={len(result.trades)} "
            f"return={result.total_return:.2%} "
            f"sharpe={sharpe} win_rate={wr}",
        )
    return 0


def _cmd_forecast() -> int:
    """Generate forecasts for all ETFs based on current signals and backtests."""
    from app.strategy.forecast import generate_forecast, save_forecast

    # Load signals from saved scheduler output
    signals_path = Path("data/scheduler_status.json")
    signals_data: list[dict[str, object]] = []
    backtest_data: list[dict[str, object]] = []

    if signals_path.exists():
        try:
            status = json.loads(signals_path.read_text(encoding="utf-8"))
            results = status.get("results", [])
            for r in results:
                if not isinstance(r, dict):
                    continue
                name = r.get("name", "")
                output = r.get("output", "")
                if name == "etf.signals" and output:
                    parsed = json.loads(output)
                    if isinstance(parsed, list):
                        signals_data = parsed
                elif name == "strategy.backtest-all" and output:
                    parsed = json.loads(output)
                    if isinstance(parsed, list):
                        backtest_data = parsed
        except (json.JSONDecodeError, OSError):
            pass

    if not signals_data:
        print("No signal data available. Run scheduler first.")  # noqa: T201
        return 1

    report = generate_forecast(signals_data, backtest_data)
    save_forecast(report)

    output = asdict(report)
    # Trim factor_scores for cleaner stdout (scheduler parses this as JSON)
    for fc in output.get("forecasts", []):
        fc.pop("factor_scores", None)
    print(json.dumps(output, indent=2))  # noqa: T201
    return 0


def _cmd_verify() -> int:
    """Verify past forecasts against actual outcomes."""
    from app.strategy.verify import verify_forecasts

    # Load current signals and backtest data
    signals_path = Path("data/scheduler_status.json")
    signals_data: list[dict[str, object]] = []
    backtest_data: list[dict[str, object]] = []

    if signals_path.exists():
        try:
            status = json.loads(signals_path.read_text(encoding="utf-8"))
            results = status.get("results", [])
            for r in results:
                if not isinstance(r, dict):
                    continue
                name = r.get("name", "")
                output = r.get("output", "")
                if name == "etf.signals" and output:
                    parsed = json.loads(output)
                    if isinstance(parsed, list):
                        signals_data = parsed
                elif name == "strategy.backtest-all" and output:
                    parsed = json.loads(output)
                    if isinstance(parsed, list):
                        backtest_data = parsed
        except (json.JSONDecodeError, OSError):
            pass

    report = verify_forecasts(signals_data, backtest_data)

    output = asdict(report)
    # Trim individual verifications for cleaner output
    output.pop("verifications", None)
    print(json.dumps(output, indent=2))  # noqa: T201
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
        case "backtest-all":
            return _cmd_backtest_all(args)
        case "strategies":
            return _cmd_strategies()
        case "forecast":
            return _cmd_forecast()
        case "verify":
            return _cmd_verify()
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

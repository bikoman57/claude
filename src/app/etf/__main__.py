from __future__ import annotations

import json
import sys
from dataclasses import asdict

from app.etf.drawdown import calculate_all_drawdowns, calculate_drawdown
from app.etf.signals import (
    SignalState,
    capture_signal_factors,
    evaluate_signal,
)
from app.etf.stats import calculate_recovery_stats
from app.etf.store import (
    get_active_signals,
    load_signals,
    save_signals,
)
from app.etf.universe import (
    ETF_UNIVERSE,
    get_all_underlying_tickers,
    get_mapping,
    get_mapping_by_underlying,
)
from app.history.outcomes import record_entry, record_exit

USAGE = """\
Usage:
  uv run python -m app.etf scan                    Scan all underlyings
  uv run python -m app.etf drawdown <ticker>        Check one underlying
  uv run python -m app.etf signals                  List current signals
  uv run python -m app.etf active                   List active positions
  uv run python -m app.etf stats <ticker> <pct>     Recovery stats
  uv run python -m app.etf universe                 Print ETF universe
  uv run python -m app.etf enter <ticker> <price>   Record entry
  uv run python -m app.etf close <ticker> [price]   Close position
"""


def cmd_universe() -> int:
    """Print the ETF universe table."""
    header = (
        f"{'Leveraged':<10} {'Underlying':<10} {'Name':<28}"
        f" {'Lev':>4} {'DD%':>5} {'Alert%':>7} {'Target%':>8}"
    )
    print(header)  # noqa: T201
    print("-" * 80)  # noqa: T201
    for m in ETF_UNIVERSE:
        row = (
            f"{m.leveraged_ticker:<10} {m.underlying_ticker:<10}"
            f" {m.name:<28} {m.leverage:>4.0f}x"
            f" {m.drawdown_threshold:>4.0%}"
            f" {m.alert_threshold:>6.0%}"
            f" {m.profit_target:>7.0%}"
        )
        print(row)  # noqa: T201
    return 0


def cmd_drawdown(ticker: str) -> int:
    """Check drawdown for one underlying."""
    result = calculate_drawdown(ticker.upper())
    print(json.dumps(asdict(result), indent=2))  # noqa: T201
    return 0


def cmd_scan() -> int:
    """Scan all underlyings and evaluate signals."""
    tickers = get_all_underlying_tickers()
    drawdowns = calculate_all_drawdowns(tickers)

    signals = []
    for dd in drawdowns:
        mapping = get_mapping_by_underlying(dd.ticker)
        if mapping is None:
            continue
        sig = evaluate_signal(mapping, dd)
        signals.append(sig)

    save_signals(signals)

    icons = {
        "WATCH": "  ",
        "ALERT": "! ",
        "SIGNAL": ">>",
        "ACTIVE": "* ",
        "TARGET": "$$",
    }
    for sig in signals:
        prefix = icons.get(sig.state, "  ")
        dd_pct = abs(sig.underlying_drawdown_pct) * 100
        print(  # noqa: T201
            f"{prefix} {sig.leveraged_ticker:<6} {sig.state:<7}"
            f" {sig.underlying_ticker} down {dd_pct:.1f}%"
            f" from ATH (${sig.underlying_ath:.2f})"
        )
    return 0


def cmd_signals() -> int:
    """List all current signals."""
    signals = load_signals()
    if not signals:
        print("No signals stored. Run 'scan' first.")  # noqa: T201
        return 0
    print(json.dumps([asdict(s) for s in signals], indent=2))  # noqa: T201
    return 0


def cmd_active() -> int:
    """List active positions."""
    active = get_active_signals()
    if not active:
        print("No active positions.")  # noqa: T201
        return 0
    for sig in active:
        pl = (
            f"{sig.current_pl_pct:+.1%}"
            if sig.current_pl_pct is not None
            else "n/a"
        )
        print(  # noqa: T201
            f"{sig.leveraged_ticker}:"
            f" entry ${sig.leveraged_entry_price}"
            f" | current ${sig.leveraged_current_price}"
            f" | P/L {pl}"
            f" | target +{sig.profit_target_pct:.0%}"
        )
    return 0


def cmd_stats(ticker: str, threshold: str) -> int:
    """Print historical recovery stats."""
    stats = calculate_recovery_stats(ticker.upper(), float(threshold))
    print(json.dumps(asdict(stats), indent=2))  # noqa: T201
    return 0


def cmd_enter(ticker: str, price: str) -> int:
    """Record a position entry: SIGNAL -> ACTIVE."""
    signals = load_signals()
    found_sig = None
    for sig in signals:
        if (
            sig.leveraged_ticker == ticker.upper()
            and sig.state == SignalState.SIGNAL
        ):
            sig.state = SignalState.ACTIVE
            sig.leveraged_entry_price = float(price)
            found_sig = sig
            break

    if found_sig is None:
        print(  # noqa: T201
            f"Error: no SIGNAL found for {ticker.upper()}",
            file=sys.stderr,
        )
        return 1

    save_signals(signals)

    # Record trade outcome for learning
    mapping = get_mapping(ticker.upper())
    factors: dict[str, str] = {}
    if mapping is not None:
        factors = capture_signal_factors(found_sig, mapping)
    record_entry(
        leveraged_ticker=ticker.upper(),
        underlying_ticker=found_sig.underlying_ticker,
        entry_price=float(price),
        factors=factors,
    )
    print(  # noqa: T201
        f"Entered {ticker.upper()} at ${price}"
        " (outcome recorded)",
    )
    return 0


def cmd_close(ticker: str, exit_price: str | None = None) -> int:
    """Close a position and remove from signals."""
    signals = load_signals()
    before = len(signals)
    signals = [
        s for s in signals if s.leveraged_ticker != ticker.upper()
    ]
    if len(signals) == before:
        print(  # noqa: T201
            f"Error: no position found for {ticker.upper()}",
            file=sys.stderr,
        )
        return 1

    save_signals(signals)

    # Record trade exit for learning
    if exit_price is not None:
        result = record_exit(ticker.upper(), float(exit_price))
        if result and result.pl_pct is not None:
            print(  # noqa: T201
                f"Closed {ticker.upper()} at ${exit_price}"
                f" (P/L: {result.pl_pct:+.1%})",
            )
        else:
            print(  # noqa: T201
                f"Closed {ticker.upper()} at ${exit_price}",
            )
    else:
        print(  # noqa: T201
            f"Closed {ticker.upper()}"
            " (no exit price — outcome not recorded)",
        )
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]

    match command:
        case "universe":
            exit_code = cmd_universe()
        case "drawdown" if len(sys.argv) >= 3:
            exit_code = cmd_drawdown(sys.argv[2])
        case "scan":
            exit_code = cmd_scan()
        case "signals":
            exit_code = cmd_signals()
        case "active":
            exit_code = cmd_active()
        case "stats" if len(sys.argv) >= 4:
            exit_code = cmd_stats(sys.argv[2], sys.argv[3])
        case "enter" if len(sys.argv) >= 4:
            exit_code = cmd_enter(sys.argv[2], sys.argv[3])
        case "close" if len(sys.argv) >= 4:
            exit_code = cmd_close(sys.argv[2], sys.argv[3])
        case "close" if len(sys.argv) >= 3:
            exit_code = cmd_close(sys.argv[2])
        case _:
            print(  # noqa: T201
                f"Unknown command: {command}",
                file=sys.stderr,
            )
            print(USAGE, file=sys.stderr)  # noqa: T201
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

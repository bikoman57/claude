"""Quantitative research CLI."""

from __future__ import annotations

import sys

USAGE = """\
Usage:
  uv run python -m app.quant regime           Market regime detection
  uv run python -m app.quant recovery-stats   Drawdown recovery analysis
  uv run python -m app.quant factor-test      Factor significance testing
  uv run python -m app.quant summary          Full quantitative summary
"""


def cmd_regime() -> int:
    """Detect current market regime."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance required: uv add yfinance")  # noqa: T201
        return 1

    from app.quant.regime import detect_regime

    tickers = [("SPY", "S&P 500"), ("QQQ", "Nasdaq-100"), ("IWM", "Russell 2000")]
    print("=== MARKET REGIME ===")  # noqa: T201

    for ticker, name in tickers:
        t = yf.Ticker(ticker)
        h = t.history(period="1y")
        if len(h) < 61:
            print(f"{name}: insufficient data")  # noqa: T201
            continue
        closes = h["Close"].tolist()
        result = detect_regime(closes)
        print(  # noqa: T201
            f"{name}: {result.regime} ({result.confidence_pct:.0f}% confidence)"
            f" | 60d return: {result.return_60d:+.1%}"
            f" | ann. vol: {result.volatility_ann:.1%}"
        )
    return 0


def cmd_recovery_stats() -> int:
    """Analyze drawdown recovery distributions."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance required: uv add yfinance")  # noqa: T201
        return 1

    from app.etf.universe import ETF_UNIVERSE
    from app.quant.recovery import analyze_recovery

    print("=== RECOVERY STATISTICS ===")  # noqa: T201
    for m in ETF_UNIVERSE:
        t = yf.Ticker(m.underlying_ticker)
        h = t.history(period="10y")
        if len(h) < 100:
            continue
        closes = h["Close"].tolist()
        stats = analyze_recovery(closes, threshold_pct=m.drawdown_threshold)
        if stats.episode_count > 0:
            print(  # noqa: T201
                f"{m.underlying_ticker} (>{stats.threshold_pct:.0%} drawdowns):"
                f" {stats.episode_count} episodes"
                f" | median: {stats.median_days:.0f}d"
                f" | 95% CI: [{stats.ci_low_days:.0f}-{stats.ci_high_days:.0f}d]"
                f" | recovery rate: {stats.recovery_rate:.0%}"
            )
    return 0


def cmd_factor_test() -> int:
    """Test factor significance from trade history."""
    print("=== FACTOR SIGNIFICANCE ===")  # noqa: T201
    print("Requires completed trade history. Run after completing trades.")  # noqa: T201
    return 0


def cmd_summary() -> int:
    """Full quantitative summary."""
    print("=== QUANTITATIVE SUMMARY ===\n")  # noqa: T201
    cmd_regime()
    print()  # noqa: T201
    cmd_recovery_stats()
    print()  # noqa: T201
    cmd_factor_test()
    return 0


def main() -> int:
    """CLI entry point."""
    args = sys.argv[1:]
    if not args:
        print(USAGE)  # noqa: T201
        return 1

    commands = {
        "regime": cmd_regime,
        "recovery-stats": cmd_recovery_stats,
        "factor-test": cmd_factor_test,
        "summary": cmd_summary,
    }

    cmd = args[0]
    if cmd not in commands:
        print(f"Unknown command: {cmd}")  # noqa: T201
        print(USAGE)  # noqa: T201
        return 1

    return commands[cmd]()


if __name__ == "__main__":
    raise SystemExit(main())

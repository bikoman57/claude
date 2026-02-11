from __future__ import annotations

import math
from dataclasses import dataclass

import yfinance as yf


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Configuration for a single backtest run."""

    underlying_ticker: str
    leverage: float
    entry_threshold: float  # drawdown % to enter (e.g. 0.05 = 5%)
    profit_target: float  # exit gain % (e.g. 0.10 = 10%)
    stop_loss: float  # exit loss % (e.g. 0.15 = 15%)
    period: str  # yfinance period (e.g. "2y", "5y")


@dataclass(frozen=True, slots=True)
class BacktestTrade:
    """One simulated trade."""

    entry_day: int
    exit_day: int
    entry_price: float
    exit_price: float
    drawdown_at_entry: float
    leveraged_return: float
    exit_reason: str  # "target", "stop", "end_of_period"


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Full result of a backtest run."""

    config: BacktestConfig
    trades: tuple[BacktestTrade, ...]
    total_return: float
    sharpe_ratio: float | None
    max_drawdown: float
    win_rate: float | None
    avg_gain: float | None
    avg_loss: float | None
    total_days: int


def _calculate_sharpe(
    returns: list[float],
    risk_free_annual: float = 0.04,
) -> float | None:
    """Calculate annualized Sharpe ratio from a list of trade returns."""
    if len(returns) < 2:
        return None
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance)
    if std_r < 1e-12:
        return None
    # Approximate annualization: assume ~12 trades/year
    trades_per_year = min(len(returns), 12)
    annual_mean = mean_r * trades_per_year
    annual_std = std_r * math.sqrt(trades_per_year)
    return (annual_mean - risk_free_annual) / annual_std


def run_backtest(config: BacktestConfig) -> BacktestResult | None:
    """Run a backtest simulation on historical data.

    Algorithm:
    1. Fetch underlying close prices via yfinance.
    2. Track running ATH and drawdown at each day.
    3. When drawdown >= entry_threshold, enter a trade.
    4. Track leveraged return = underlying_return * leverage.
    5. Exit when profit target, stop loss, or end of period.

    Note: Simplified leveraged return ignores daily compounding
    and volatility decay effects of actual leveraged ETFs.
    """
    try:
        ticker = yf.Ticker(config.underlying_ticker)
        hist = ticker.history(period=config.period)
    except Exception:
        return None

    if len(hist) < 20:
        return None

    closes = [float(c) for c in hist["Close"]]
    total_days = len(closes)

    trades: list[BacktestTrade] = []
    ath = closes[0]
    in_trade = False
    entry_day = 0
    entry_price = 0.0
    drawdown_at_entry = 0.0

    for i, price in enumerate(closes):
        if price > ath:
            ath = price

        drawdown = (ath - price) / ath if ath > 0 else 0.0

        if not in_trade:
            if drawdown >= config.entry_threshold:
                in_trade = True
                entry_day = i
                entry_price = price
                drawdown_at_entry = drawdown
        else:
            underlying_return = (price - entry_price) / entry_price
            leveraged_return = underlying_return * config.leverage

            exit_reason = ""
            if leveraged_return >= config.profit_target:
                exit_reason = "target"
            elif leveraged_return <= -config.stop_loss:
                exit_reason = "stop"
            elif i == total_days - 1:
                exit_reason = "end_of_period"

            if exit_reason:
                trades.append(
                    BacktestTrade(
                        entry_day=entry_day,
                        exit_day=i,
                        entry_price=entry_price,
                        exit_price=price,
                        drawdown_at_entry=drawdown_at_entry,
                        leveraged_return=leveraged_return,
                        exit_reason=exit_reason,
                    ),
                )
                in_trade = False
                # Reset ATH to current price after exit
                ath = price

    # Compute statistics
    returns = [t.leveraged_return for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    win_rate = len(wins) / len(returns) if returns else None
    avg_gain = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None

    # Total return (compounded)
    total_return = 1.0
    for r in returns:
        total_return *= 1.0 + r
    total_return -= 1.0

    # Max drawdown of equity curve
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= 1.0 + r
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    sharpe = _calculate_sharpe(returns)

    return BacktestResult(
        config=config,
        trades=tuple(trades),
        total_return=total_return,
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        win_rate=win_rate,
        avg_gain=avg_gain,
        avg_loss=avg_loss,
        total_days=total_days,
    )

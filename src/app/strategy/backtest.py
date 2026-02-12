from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import yfinance as yf


class StrategyType(StrEnum):
    """Supported backtest strategy types."""

    ATH_MEAN_REVERSION = "ath_mean_reversion"
    RSI_OVERSOLD = "rsi_oversold"
    BOLLINGER_LOWER = "bollinger_lower"
    MA_DIP = "ma_dip"


# Human-readable descriptions for each strategy type
STRATEGY_DESCRIPTIONS: dict[StrategyType, str] = {
    StrategyType.ATH_MEAN_REVERSION: "Buy when underlying draws down from ATH",
    StrategyType.RSI_OVERSOLD: "Buy when RSI(14) drops below threshold",
    StrategyType.BOLLINGER_LOWER: "Buy when price touches lower Bollinger Band",
    StrategyType.MA_DIP: "Buy when price dips below 50-day moving average",
}

# What entry_threshold means per strategy
THRESHOLD_LABELS: dict[StrategyType, str] = {
    StrategyType.ATH_MEAN_REVERSION: "drawdown %",
    StrategyType.RSI_OVERSOLD: "RSI level",
    StrategyType.BOLLINGER_LOWER: "std deviations",
    StrategyType.MA_DIP: "% below MA",
}


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Configuration for a single backtest run.

    entry_threshold meaning depends on strategy_type:
    - ATH_MEAN_REVERSION: drawdown fraction (0.05 = 5% drawdown from ATH)
    - RSI_OVERSOLD: RSI level to enter (30 = buy when RSI < 30)
    - BOLLINGER_LOWER: std deviations for lower band (2.0 = 2-sigma)
    - MA_DIP: fraction below 50-day MA (0.03 = 3% below MA)
    """

    underlying_ticker: str
    leverage: float
    entry_threshold: float
    profit_target: float  # exit gain % (e.g. 0.10 = 10%)
    stop_loss: float  # exit loss % (e.g. 0.15 = 15%)
    period: str  # yfinance period (e.g. "2y", "5y")
    strategy_type: str = StrategyType.ATH_MEAN_REVERSION


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
    entry_date: str = ""  # YYYY-MM-DD, populated when historical dates available
    exit_date: str = ""  # YYYY-MM-DD, populated when historical dates available


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


def _compute_rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Compute RSI(period) for each day. Returns None for first `period` days."""
    rsi: list[float | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return rsi

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss < 1e-12:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss < 1e-12:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def _compute_bollinger(
    closes: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> list[tuple[float, float, float] | None]:
    """Compute Bollinger Bands. Returns (lower, middle, upper) or None."""
    bands: list[tuple[float, float, float] | None] = [None] * len(closes)
    if len(closes) < period:
        return bands

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(variance)
        bands[i] = (mean - num_std * std, mean, mean + num_std * std)

    return bands


def _compute_ma(
    closes: list[float],
    period: int = 50,
) -> list[float | None]:
    """Compute simple moving average. Returns None before enough data."""
    ma: list[float | None] = [None] * len(closes)
    if len(closes) < period:
        return ma

    running_sum = sum(closes[:period])
    ma[period - 1] = running_sum / period

    for i in range(period, len(closes)):
        running_sum += closes[i] - closes[i - period]
        ma[i] = running_sum / period

    return ma


def _build_result(
    config: BacktestConfig,
    trades: list[BacktestTrade],
    total_days: int,
) -> BacktestResult:
    """Compute statistics from trades and build BacktestResult."""
    returns = [t.leveraged_return for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    win_rate = len(wins) / len(returns) if returns else None
    avg_gain = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None

    total_return = 1.0
    for r in returns:
        total_return *= 1.0 + r
    total_return -= 1.0

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


def _check_exit(
    price: float,
    entry_price: float,
    leverage: float,
    profit_target: float,
    stop_loss: float,
    is_last_day: bool,
) -> str:
    """Check exit conditions. Returns exit reason or empty string."""
    underlying_return = (price - entry_price) / entry_price
    leveraged_return = underlying_return * leverage
    if leveraged_return >= profit_target:
        return "target"
    if leveraged_return <= -stop_loss:
        return "stop"
    if is_last_day:
        return "end_of_period"
    return ""


def _run_ath_mean_reversion(
    config: BacktestConfig,
    closes: list[float],
) -> list[BacktestTrade]:
    """ATH mean-reversion: enter when drawdown from ATH exceeds threshold."""
    trades: list[BacktestTrade] = []
    ath = closes[0]
    in_trade = False
    entry_day = 0
    entry_price = 0.0
    drawdown_at_entry = 0.0
    total_days = len(closes)

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
            exit_reason = _check_exit(
                price,
                entry_price,
                config.leverage,
                config.profit_target,
                config.stop_loss,
                i == total_days - 1,
            )
            if exit_reason:
                underlying_return = (price - entry_price) / entry_price
                trades.append(
                    BacktestTrade(
                        entry_day=entry_day,
                        exit_day=i,
                        entry_price=entry_price,
                        exit_price=price,
                        drawdown_at_entry=drawdown_at_entry,
                        leveraged_return=underlying_return * config.leverage,
                        exit_reason=exit_reason,
                    ),
                )
                in_trade = False
                ath = price

    return trades


def _run_rsi_oversold(
    config: BacktestConfig,
    closes: list[float],
) -> list[BacktestTrade]:
    """RSI oversold: enter when RSI(14) drops below threshold."""
    rsi = _compute_rsi(closes, period=14)
    trades: list[BacktestTrade] = []
    in_trade = False
    entry_day = 0
    entry_price = 0.0
    rsi_at_entry = 0.0
    total_days = len(closes)

    for i, price in enumerate(closes):
        rsi_val = rsi[i]
        if rsi_val is None:
            continue

        if not in_trade:
            if rsi_val < config.entry_threshold:
                in_trade = True
                entry_day = i
                entry_price = price
                rsi_at_entry = rsi_val
        else:
            exit_reason = _check_exit(
                price,
                entry_price,
                config.leverage,
                config.profit_target,
                config.stop_loss,
                i == total_days - 1,
            )
            if exit_reason:
                underlying_return = (price - entry_price) / entry_price
                trades.append(
                    BacktestTrade(
                        entry_day=entry_day,
                        exit_day=i,
                        entry_price=entry_price,
                        exit_price=price,
                        drawdown_at_entry=rsi_at_entry / 100.0,
                        leveraged_return=underlying_return * config.leverage,
                        exit_reason=exit_reason,
                    ),
                )
                in_trade = False

    return trades


def _run_bollinger_lower(
    config: BacktestConfig,
    closes: list[float],
) -> list[BacktestTrade]:
    """Bollinger lower band: enter when price touches lower band."""
    bands = _compute_bollinger(closes, period=20, num_std=config.entry_threshold)
    trades: list[BacktestTrade] = []
    in_trade = False
    entry_day = 0
    entry_price = 0.0
    band_dist = 0.0
    total_days = len(closes)

    for i, price in enumerate(closes):
        band = bands[i]
        if band is None:
            continue
        lower, middle, _upper = band

        if not in_trade:
            if price <= lower and middle > 0:
                in_trade = True
                entry_day = i
                entry_price = price
                band_dist = (middle - price) / middle
        else:
            exit_reason = _check_exit(
                price,
                entry_price,
                config.leverage,
                config.profit_target,
                config.stop_loss,
                i == total_days - 1,
            )
            if exit_reason:
                underlying_return = (price - entry_price) / entry_price
                trades.append(
                    BacktestTrade(
                        entry_day=entry_day,
                        exit_day=i,
                        entry_price=entry_price,
                        exit_price=price,
                        drawdown_at_entry=band_dist,
                        leveraged_return=underlying_return * config.leverage,
                        exit_reason=exit_reason,
                    ),
                )
                in_trade = False

    return trades


def _run_ma_dip(
    config: BacktestConfig,
    closes: list[float],
) -> list[BacktestTrade]:
    """MA dip: enter when price dips below 50-day MA by threshold %."""
    ma = _compute_ma(closes, period=50)
    trades: list[BacktestTrade] = []
    in_trade = False
    entry_day = 0
    entry_price = 0.0
    ma_dist = 0.0
    total_days = len(closes)

    for i, price in enumerate(closes):
        ma_val = ma[i]
        if ma_val is None or ma_val <= 0:
            continue

        pct_below = (ma_val - price) / ma_val

        if not in_trade:
            if pct_below >= config.entry_threshold:
                in_trade = True
                entry_day = i
                entry_price = price
                ma_dist = pct_below
        else:
            exit_reason = _check_exit(
                price,
                entry_price,
                config.leverage,
                config.profit_target,
                config.stop_loss,
                i == total_days - 1,
            )
            if exit_reason:
                underlying_return = (price - entry_price) / entry_price
                trades.append(
                    BacktestTrade(
                        entry_day=entry_day,
                        exit_day=i,
                        entry_price=entry_price,
                        exit_price=price,
                        drawdown_at_entry=ma_dist,
                        leveraged_return=underlying_return * config.leverage,
                        exit_reason=exit_reason,
                    ),
                )
                in_trade = False

    return trades


_STRATEGY_RUNNERS = {
    StrategyType.ATH_MEAN_REVERSION: _run_ath_mean_reversion,
    StrategyType.RSI_OVERSOLD: _run_rsi_oversold,
    StrategyType.BOLLINGER_LOWER: _run_bollinger_lower,
    StrategyType.MA_DIP: _run_ma_dip,
}


def run_backtest(config: BacktestConfig) -> BacktestResult | None:
    """Run a backtest simulation on historical data.

    Dispatches to the appropriate strategy runner based on config.strategy_type.
    All strategies share the same exit logic (profit target, stop loss).

    Note: Simplified leveraged return ignores daily compounding
    and volatility decay effects of actual leveraged ETFs.
    """
    try:
        ticker = yf.Ticker(config.underlying_ticker)
        hist = ticker.history(period=config.period)
    except Exception:
        return None

    if len(hist) < 50:
        return None

    closes = [float(c) for c in hist["Close"]]
    total_days = len(closes)

    # Extract calendar dates from DataFrame index
    dates: list[str] = []
    for d in hist.index:
        try:
            dates.append(d.strftime("%Y-%m-%d"))
        except (AttributeError, ValueError):
            dates.append("")

    try:
        strategy_type = StrategyType(config.strategy_type)
    except ValueError:
        return None
    runner = _STRATEGY_RUNNERS.get(strategy_type)
    if runner is None:
        return None

    trades = runner(config, closes)

    # Enrich trades with calendar dates
    if dates:
        enriched = []
        for t in trades:
            entry_dt = dates[t.entry_day] if t.entry_day < len(dates) else ""
            exit_dt = dates[t.exit_day] if t.exit_day < len(dates) else ""
            enriched.append(
                BacktestTrade(
                    entry_day=t.entry_day,
                    exit_day=t.exit_day,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    drawdown_at_entry=t.drawdown_at_entry,
                    leveraged_return=t.leveraged_return,
                    exit_reason=t.exit_reason,
                    entry_date=entry_dt,
                    exit_date=exit_dt,
                )
            )
        trades = enriched

    return _build_result(config, trades, total_days)

from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf


@dataclass(frozen=True, slots=True)
class RecoveryStats:
    """Historical recovery statistics from a given drawdown threshold."""

    ticker: str
    threshold_pct: float
    total_episodes: int
    avg_recovery_days: float
    median_recovery_days: float
    min_recovery_days: int
    max_recovery_days: int
    recovery_rate: float


def calculate_recovery_stats(
    ticker: str,
    threshold: float,
    period: str = "10y",
) -> RecoveryStats:
    """Analyze historical drawdown episodes and recovery times.

    Finds every instance where the ticker dropped >= threshold from its
    running ATH, then measures how many trading days each recovery took.
    """
    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    if hist.empty:
        msg = f"No data for {ticker}"
        raise ValueError(msg)

    closes = hist["Close"]
    running_max = closes.cummax()
    drawdowns = (closes - running_max) / running_max

    in_drawdown = False
    episodes: list[int] = []
    start_idx = 0

    for i in range(len(drawdowns)):
        dd = float(drawdowns.iloc[i])
        if not in_drawdown and dd <= -threshold:
            in_drawdown = True
            start_idx = i
        elif in_drawdown and dd >= 0:
            in_drawdown = False
            episodes.append(i - start_idx)

    total = len(episodes) + (1 if in_drawdown else 0)

    if not episodes:
        return RecoveryStats(
            ticker=ticker,
            threshold_pct=threshold,
            total_episodes=total,
            avg_recovery_days=0.0,
            median_recovery_days=0.0,
            min_recovery_days=0,
            max_recovery_days=0,
            recovery_rate=0.0,
        )

    episodes_sorted = sorted(episodes)
    mid = len(episodes_sorted) // 2
    median = float(
        episodes_sorted[mid]
        if len(episodes_sorted) % 2 == 1
        else (episodes_sorted[mid - 1] + episodes_sorted[mid]) / 2
    )

    return RecoveryStats(
        ticker=ticker,
        threshold_pct=threshold,
        total_episodes=total,
        avg_recovery_days=sum(episodes) / len(episodes),
        median_recovery_days=median,
        min_recovery_days=min(episodes),
        max_recovery_days=max(episodes),
        recovery_rate=len(episodes) / total if total > 0 else 0.0,
    )

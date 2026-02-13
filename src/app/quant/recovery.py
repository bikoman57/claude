"""Drawdown recovery distribution analysis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class RecoveryStats:
    """Statistics on drawdown recovery times."""

    threshold_pct: float
    episode_count: int
    median_days: float
    mean_days: float
    ci_low_days: float
    ci_high_days: float
    recovery_rate: float
    method: str


def analyze_recovery(
    closes: list[float],
    threshold_pct: float = 0.05,
) -> RecoveryStats:
    """Analyze drawdown recovery distribution.

    Finds all episodes where the price drew down more than threshold_pct
    from the running ATH, and measures how long each took to recover.
    """
    if len(closes) < 20:
        return RecoveryStats(
            threshold_pct=threshold_pct,
            episode_count=0,
            median_days=0.0,
            mean_days=0.0,
            ci_low_days=0.0,
            ci_high_days=0.0,
            recovery_rate=0.0,
            method="insufficient_data",
        )

    arr = np.array(closes)
    ath = np.maximum.accumulate(arr)
    drawdown = (arr - ath) / ath

    # Find episodes
    in_episode = False
    episode_start = 0
    recovery_times: list[int] = []
    unrecovered = 0

    for i in range(len(drawdown)):
        if not in_episode and drawdown[i] <= -threshold_pct:
            in_episode = True
            episode_start = i
        elif in_episode and drawdown[i] >= 0:
            recovery_times.append(i - episode_start)
            in_episode = False

    if in_episode:
        unrecovered = 1

    total_episodes = len(recovery_times) + unrecovered

    if not recovery_times:
        return RecoveryStats(
            threshold_pct=threshold_pct,
            episode_count=total_episodes,
            median_days=0.0,
            mean_days=0.0,
            ci_low_days=0.0,
            ci_high_days=0.0,
            recovery_rate=0.0,
            method="no_recoveries",
        )

    times = np.array(recovery_times, dtype=float)
    recovery_rate = len(recovery_times) / total_episodes if total_episodes > 0 else 0.0

    return RecoveryStats(
        threshold_pct=threshold_pct,
        episode_count=total_episodes,
        median_days=float(np.median(times)),
        mean_days=float(np.mean(times)),
        ci_low_days=float(np.percentile(times, 2.5)),
        ci_high_days=float(np.percentile(times, 97.5)),
        recovery_rate=round(recovery_rate, 3),
        method="empirical",
    )

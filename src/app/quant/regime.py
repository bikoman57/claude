"""Market regime detection via rolling statistics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class Regime(StrEnum):
    """Market regime classification."""

    BULL = "BULL"
    BEAR = "BEAR"
    RANGE = "RANGE"


@dataclass(frozen=True, slots=True)
class RegimeResult:
    """Regime detection result."""

    regime: Regime
    confidence_pct: float
    return_60d: float
    volatility_ann: float
    method: str


def detect_regime(
    closes: list[float],
    *,
    window: int = 60,
    bull_return_threshold: float = 0.05,
    bear_return_threshold: float = -0.05,
    high_vol_threshold: float = 0.25,
) -> RegimeResult:
    """Detect market regime from closing prices.

    Uses rolling 60-day return and annualized volatility.
    """
    if len(closes) < window + 1:
        return RegimeResult(
            regime=Regime.RANGE,
            confidence_pct=0.0,
            return_60d=0.0,
            volatility_ann=0.0,
            method="insufficient_data",
        )

    arr = np.array(closes)
    ret_60d = float((arr[-1] / arr[-window - 1]) - 1)

    daily_returns = np.diff(arr) / arr[:-1]
    recent_returns = daily_returns[-window:]
    vol_ann = float(np.std(recent_returns) * np.sqrt(252))

    if ret_60d > bull_return_threshold and vol_ann < high_vol_threshold:
        regime = Regime.BULL
        confidence = min(abs(ret_60d) / 0.15 * 100, 95.0)
    elif ret_60d < bear_return_threshold or vol_ann > high_vol_threshold:
        regime = Regime.BEAR
        confidence = min(
            (abs(ret_60d) / 0.15 + vol_ann / 0.40) / 2 * 100,
            95.0,
        )
    else:
        regime = Regime.RANGE
        confidence = max(50.0, 100.0 - abs(ret_60d) / 0.10 * 100)

    return RegimeResult(
        regime=regime,
        confidence_pct=round(confidence, 1),
        return_60d=round(ret_60d, 4),
        volatility_ann=round(vol_ann, 4),
        method="rolling_stats",
    )

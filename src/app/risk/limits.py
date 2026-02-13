"""Risk limits and portfolio constraint definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Portfolio risk limits.

    These defaults are conservative for a leveraged ETF portfolio.
    """

    max_concurrent_positions: int = 4
    max_single_position_pct: float = 0.30
    max_sector_exposure_pct: float = 0.50
    max_total_leveraged_exposure: float = 3.0
    min_cash_reserve_pct: float = 0.20


# Default risk limits used across the system
DEFAULT_LIMITS = RiskLimits()

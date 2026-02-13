"""Veto logic for entry signals that would exceed risk limits."""

from __future__ import annotations

from dataclasses import dataclass

from app.risk.exposure import ExposureReport, Position, get_sector
from app.risk.limits import DEFAULT_LIMITS, RiskLimits


@dataclass(frozen=True, slots=True)
class VetoResult:
    """Result of veto check for a proposed entry."""

    vetoed: bool
    reasons: tuple[str, ...]
    leveraged_ticker: str


def check_veto(
    proposed_ticker: str,
    proposed_value: float,
    exposure: ExposureReport,
    positions: list[Position],
    limits: RiskLimits = DEFAULT_LIMITS,
) -> VetoResult:
    """Check if a proposed entry would violate risk limits.

    Returns a VetoResult with vetoed=True if any limit would be breached.
    """
    reasons: list[str] = []

    # 1. Max concurrent positions
    if exposure.position_count >= limits.max_concurrent_positions:
        reasons.append(
            f"Max positions reached: {exposure.position_count}"
            f"/{limits.max_concurrent_positions}"
        )

    # 2. Single position size
    if exposure.total_value > 0:
        position_pct = proposed_value / exposure.total_value
        if position_pct > limits.max_single_position_pct:
            reasons.append(
                f"Position too large: {position_pct:.0%} > "
                f"{limits.max_single_position_pct:.0%} limit"
            )

    # 3. Sector concentration
    sector = get_sector(proposed_ticker)
    current_sector = exposure.sector_pcts.get(sector, 0.0)
    new_sector_pct = (
        current_sector + proposed_value / exposure.total_value
        if exposure.total_value > 0
        else 0.0
    )
    if new_sector_pct > limits.max_sector_exposure_pct:
        reasons.append(
            f"Sector {sector} would be {new_sector_pct:.0%} > "
            f"{limits.max_sector_exposure_pct:.0%} limit"
        )

    # 4. Cash reserve
    if exposure.total_value > 0:
        new_cash_pct = (exposure.cash_value - proposed_value) / exposure.total_value
        if new_cash_pct < limits.min_cash_reserve_pct:
            reasons.append(
                f"Cash would drop to {new_cash_pct:.0%} < "
                f"{limits.min_cash_reserve_pct:.0%} minimum"
            )

    # 5. Correlation check (same sector as existing position)
    same_sector_positions = [p for p in positions if p.sector == sector]
    if same_sector_positions and new_sector_pct > 0.40:
        tickers = [p.leveraged_ticker for p in same_sector_positions]
        reasons.append(
            f"High correlation risk: {proposed_ticker} + "
            f"{', '.join(tickers)} all in {sector} sector"
        )

    return VetoResult(
        vetoed=len(reasons) > 0,
        reasons=tuple(reasons),
        leveraged_ticker=proposed_ticker,
    )

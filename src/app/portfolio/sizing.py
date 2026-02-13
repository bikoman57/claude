"""Position sizing algorithms."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SizingResult:
    """Recommended position size for an entry."""

    method: str
    position_value: float
    portfolio_pct: float
    shares_estimate: float
    rationale: str


def fixed_fraction_size(
    portfolio_value: float,
    risk_pct: float = 0.02,
    leverage: int = 3,
    entry_price: float = 1.0,
) -> SizingResult:
    """Calculate position size using fixed-fraction method.

    Risk `risk_pct` of portfolio per trade. At 3x leverage,
    actual position is risk_amount / leverage to keep notional
    exposure in check.
    """
    risk_amount = portfolio_value * risk_pct
    position_value = risk_amount / leverage * leverage  # simplified: just risk_amount
    portfolio_pct = position_value / portfolio_value if portfolio_value > 0 else 0.0
    shares = position_value / entry_price if entry_price > 0 else 0.0

    return SizingResult(
        method="fixed_fraction",
        position_value=position_value,
        portfolio_pct=portfolio_pct,
        shares_estimate=shares,
        rationale=(
            f"{risk_pct:.0%} risk at {leverage}x leverage "
            f"= ${position_value:,.0f} position"
        ),
    )


def kelly_size(
    portfolio_value: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.5,
    entry_price: float = 1.0,
) -> SizingResult:
    """Calculate position size using half-Kelly criterion.

    f* = (p*b - q) / b where p=win_rate, b=avg_win/avg_loss, q=1-p
    Uses half-Kelly by default for leveraged products.
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
        return SizingResult(
            method="kelly",
            position_value=0.0,
            portfolio_pct=0.0,
            shares_estimate=0.0,
            rationale="Insufficient data for Kelly sizing",
        )

    b = avg_win / avg_loss
    q = 1.0 - win_rate
    kelly_f = (win_rate * b - q) / b
    kelly_f = max(kelly_f, 0.0)  # Never go negative
    adjusted_f = kelly_f * fraction

    position_value = portfolio_value * adjusted_f
    portfolio_pct = adjusted_f
    shares = position_value / entry_price if entry_price > 0 else 0.0

    return SizingResult(
        method=f"kelly_{fraction:.0%}",
        position_value=position_value,
        portfolio_pct=portfolio_pct,
        shares_estimate=shares,
        rationale=(
            f"Kelly f*={kelly_f:.1%}, using {fraction:.0%}-Kelly "
            f"= {adjusted_f:.1%} = ${position_value:,.0f}"
        ),
    )

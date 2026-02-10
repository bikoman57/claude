from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.etf.drawdown import DrawdownResult
from app.etf.universe import ETFMapping


class SignalState(StrEnum):
    """Signal lifecycle states."""

    WATCH = "WATCH"
    ALERT = "ALERT"
    SIGNAL = "SIGNAL"
    ACTIVE = "ACTIVE"
    TARGET = "TARGET"


@dataclass
class Signal:
    """A trading signal for a leveraged ETF."""

    leveraged_ticker: str
    underlying_ticker: str
    state: SignalState
    underlying_drawdown_pct: float
    underlying_ath: float
    underlying_current: float
    leveraged_entry_price: float | None = None
    leveraged_current_price: float | None = None
    profit_target_pct: float = 0.10
    current_pl_pct: float | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat(
            timespec="seconds",
        ),
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat(
            timespec="seconds",
        ),
    )


def evaluate_signal(mapping: ETFMapping, drawdown: DrawdownResult) -> Signal:
    """Evaluate an underlying's drawdown and generate the appropriate signal state."""
    abs_drawdown = abs(drawdown.drawdown_pct)

    if abs_drawdown >= mapping.drawdown_threshold:
        state = SignalState.SIGNAL
    elif abs_drawdown >= mapping.alert_threshold:
        state = SignalState.ALERT
    else:
        state = SignalState.WATCH

    return Signal(
        leveraged_ticker=mapping.leveraged_ticker,
        underlying_ticker=mapping.underlying_ticker,
        state=state,
        underlying_drawdown_pct=drawdown.drawdown_pct,
        underlying_ath=drawdown.ath_price,
        underlying_current=drawdown.current_price,
        profit_target_pct=mapping.profit_target,
    )


def evaluate_active_position(
    signal: Signal,
    leveraged_current_price: float,
) -> Signal:
    """Update an ACTIVE position with current price and check profit target."""
    if signal.leveraged_entry_price is None:
        return signal

    entry = signal.leveraged_entry_price
    pl_pct = (leveraged_current_price - entry) / entry
    signal.leveraged_current_price = leveraged_current_price
    signal.current_pl_pct = pl_pct
    signal.state = (
        SignalState.TARGET
        if pl_pct >= signal.profit_target_pct
        else SignalState.ACTIVE
    )
    signal.updated_at = datetime.now(tz=UTC).isoformat(
        timespec="seconds",
    )
    return signal

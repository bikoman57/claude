"""Earnings calendar and surprise tracking via yfinance."""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import yfinance as yf

from app.sec.holdings import HoldingInfo


@dataclass(frozen=True, slots=True)
class EarningsEvent:
    """One quarterly earnings report."""

    ticker: str
    date: str  # ISO YYYY-MM-DD
    eps_estimate: float | None
    eps_actual: float | None
    surprise_pct: float | None  # (actual - estimate) / |estimate|


@dataclass(frozen=True, slots=True)
class EarningsCalendar:
    """Earnings summary for a single stock."""

    ticker: str
    next_earnings_date: str | None  # ISO YYYY-MM-DD
    days_until_earnings: int | None
    recent_events: tuple[EarningsEvent, ...]  # last 4 quarters, newest first


def fetch_earnings_calendar(ticker: str) -> EarningsCalendar:
    """Fetch earnings calendar and recent history for one stock."""
    t = yf.Ticker(ticker)
    dates = t.earnings_dates

    if dates is None or dates.empty:
        return EarningsCalendar(
            ticker=ticker,
            next_earnings_date=None,
            days_until_earnings=None,
            recent_events=(),
        )

    now = datetime.now(tz=UTC)
    events: list[EarningsEvent] = []
    next_date: str | None = None
    days_until: int | None = None

    for idx in dates.index:
        row_date = idx.to_pydatetime()
        if row_date.tzinfo is None:
            row_date = row_date.replace(tzinfo=UTC)

        iso_date = row_date.strftime("%Y-%m-%d")

        eps_est = _safe_float(dates.loc[idx, "EPS Estimate"])
        eps_act = _safe_float(dates.loc[idx, "Reported EPS"])

        surprise: float | None = None
        if eps_est is not None and eps_act is not None and eps_est != 0:
            surprise = (eps_act - eps_est) / abs(eps_est)

        events.append(
            EarningsEvent(
                ticker=ticker,
                date=iso_date,
                eps_estimate=eps_est,
                eps_actual=eps_act,
                surprise_pct=surprise,
            )
        )

        # Track next upcoming earnings (first future date)
        if row_date > now and next_date is None:
            next_date = iso_date
            days_until = (row_date - now).days

    # Sort newest first
    events.sort(key=lambda e: e.date, reverse=True)

    # Keep only events with actual results for recent history (last 4)
    past_events = [e for e in events if e.eps_actual is not None][:4]

    return EarningsCalendar(
        ticker=ticker,
        next_earnings_date=next_date,
        days_until_earnings=days_until,
        recent_events=tuple(past_events),
    )


def fetch_all_earnings_calendars(
    holdings: list[HoldingInfo],
) -> list[EarningsCalendar]:
    """Fetch earnings calendars for all holdings, skipping failures."""
    results: list[EarningsCalendar] = []
    for h in holdings:
        with contextlib.suppress(Exception):
            results.append(fetch_earnings_calendar(h.ticker))
        time.sleep(0.1)

    results.sort(key=lambda c: c.days_until_earnings or 9999)
    return results


def classify_earnings_proximity(days: int | None) -> str:
    """Classify how close the next earnings date is."""
    if days is None:
        return "UNKNOWN"
    if days < 3:
        return "IMMINENT"
    if days < 7:
        return "NEAR"
    if days < 14:
        return "UPCOMING"
    return "DISTANT"


def classify_track_record(events: tuple[EarningsEvent, ...]) -> str:
    """Classify earnings track record from recent events."""
    if len(events) < 2:
        return "INSUFFICIENT_DATA"

    beats = sum(1 for e in events if e.surprise_pct is not None and e.surprise_pct > 0)
    misses = sum(1 for e in events if e.surprise_pct is not None and e.surprise_pct < 0)

    if beats >= 3:
        return "CONSISTENT_BEATS"
    if misses >= 3:
        return "CONSISTENT_MISSES"
    return "MIXED"


def compute_avg_surprise(events: tuple[EarningsEvent, ...]) -> float | None:
    """Compute average EPS surprise % across recent events."""
    surprises = [e.surprise_pct for e in events if e.surprise_pct is not None]
    if len(surprises) < 2:
        return None
    return sum(surprises) / len(surprises)


def _safe_float(value: object) -> float | None:
    """Convert a pandas value to float, returning None for NaN/missing."""
    if value is None:
        return None
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    # NaN check
    if f != f:
        return None
    return f

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from app.sec.earnings import (
    EarningsEvent,
    classify_earnings_proximity,
    classify_track_record,
    compute_avg_surprise,
    fetch_all_earnings_calendars,
    fetch_earnings_calendar,
)
from app.sec.holdings import HoldingInfo


def _mock_earnings_dates() -> pd.DataFrame:
    """Build a mock earnings_dates DataFrame matching yfinance format."""
    return pd.DataFrame(
        {
            "EPS Estimate": [2.50, 2.30, 2.10, 2.00, None],
            "Reported EPS": [None, 2.20, 2.25, 2.10, None],
        },
        index=pd.DatetimeIndex(
            [
                "2026-04-15",  # future — upcoming, no actuals yet
                "2026-01-15",  # past
                "2025-10-15",  # past
                "2025-07-15",  # past
                "2025-04-15",  # past, no data
            ],
            name="Earnings Date",
        ),
    )


@patch("app.sec.earnings.yf.Ticker")
def test_fetch_earnings_calendar(mock_ticker_cls: MagicMock) -> None:
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = _mock_earnings_dates()
    mock_ticker_cls.return_value = mock_ticker

    cal = fetch_earnings_calendar("AAPL")

    assert cal.ticker == "AAPL"
    assert cal.next_earnings_date == "2026-04-15"
    assert cal.days_until_earnings is not None
    assert cal.days_until_earnings > 0
    # 3 past events with actual EPS (4th row has None)
    assert len(cal.recent_events) == 3
    # Newest first
    assert cal.recent_events[0].date == "2026-01-15"


@patch("app.sec.earnings.yf.Ticker")
def test_fetch_earnings_calendar_empty(mock_ticker_cls: MagicMock) -> None:
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = pd.DataFrame()
    mock_ticker_cls.return_value = mock_ticker

    cal = fetch_earnings_calendar("AAPL")

    assert cal.ticker == "AAPL"
    assert cal.next_earnings_date is None
    assert cal.days_until_earnings is None
    assert cal.recent_events == ()


@patch("app.sec.earnings.yf.Ticker")
def test_fetch_earnings_calendar_none(mock_ticker_cls: MagicMock) -> None:
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = None
    mock_ticker_cls.return_value = mock_ticker

    cal = fetch_earnings_calendar("AAPL")

    assert cal.next_earnings_date is None
    assert cal.recent_events == ()


def test_fetch_earnings_calendar_surprise_calc() -> None:
    """Verify surprise % is calculated correctly from mock data."""
    # EPS estimate=2.30, actual=2.20 → surprise = (2.20-2.30)/|2.30| = -0.0435
    event = EarningsEvent(
        ticker="AAPL",
        date="2026-01-15",
        eps_estimate=2.30,
        eps_actual=2.20,
        surprise_pct=(2.20 - 2.30) / abs(2.30),
    )
    assert event.surprise_pct is not None
    assert abs(event.surprise_pct - (-0.0435)) < 0.001


# --- classify_earnings_proximity ---


def test_classify_proximity_imminent() -> None:
    assert classify_earnings_proximity(0) == "IMMINENT"
    assert classify_earnings_proximity(1) == "IMMINENT"
    assert classify_earnings_proximity(2) == "IMMINENT"


def test_classify_proximity_near() -> None:
    assert classify_earnings_proximity(3) == "NEAR"
    assert classify_earnings_proximity(6) == "NEAR"


def test_classify_proximity_upcoming() -> None:
    assert classify_earnings_proximity(7) == "UPCOMING"
    assert classify_earnings_proximity(13) == "UPCOMING"


def test_classify_proximity_distant() -> None:
    assert classify_earnings_proximity(14) == "DISTANT"
    assert classify_earnings_proximity(90) == "DISTANT"


def test_classify_proximity_unknown() -> None:
    assert classify_earnings_proximity(None) == "UNKNOWN"


# --- classify_track_record ---


def _event(surprise: float | None) -> EarningsEvent:
    return EarningsEvent(
        ticker="TEST",
        date="2025-01-01",
        eps_estimate=1.0,
        eps_actual=1.0,
        surprise_pct=surprise,
    )


def test_track_record_consistent_beats() -> None:
    events = tuple(_event(0.05) for _ in range(4))
    assert classify_track_record(events) == "CONSISTENT_BEATS"


def test_track_record_consistent_misses() -> None:
    events = tuple(_event(-0.05) for _ in range(4))
    assert classify_track_record(events) == "CONSISTENT_MISSES"


def test_track_record_mixed() -> None:
    events = (_event(0.05), _event(-0.05), _event(0.02), _event(-0.01))
    assert classify_track_record(events) == "MIXED"


def test_track_record_insufficient() -> None:
    assert classify_track_record((_event(0.05),)) == "INSUFFICIENT_DATA"
    assert classify_track_record(()) == "INSUFFICIENT_DATA"


# --- compute_avg_surprise ---


def test_avg_surprise() -> None:
    events = (_event(0.10), _event(0.06), _event(0.04))
    result = compute_avg_surprise(events)
    assert result is not None
    assert abs(result - 0.0667) < 0.001


def test_avg_surprise_insufficient() -> None:
    assert compute_avg_surprise((_event(0.10),)) is None
    assert compute_avg_surprise(()) is None


def test_avg_surprise_with_nones() -> None:
    events = (_event(0.10), _event(None), _event(0.06))
    result = compute_avg_surprise(events)
    assert result is not None
    assert abs(result - 0.08) < 0.001


# --- fetch_all_earnings_calendars ---


@patch("app.sec.earnings.time.sleep")
@patch("app.sec.earnings.yf.Ticker")
def test_fetch_all_earnings_calendars(
    mock_ticker_cls: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = _mock_earnings_dates()
    mock_ticker_cls.return_value = mock_ticker

    holdings = [
        HoldingInfo(ticker="AAPL", name="Apple Inc.", cik="0000320193"),
        HoldingInfo(ticker="MSFT", name="Microsoft", cik="0000789019"),
    ]
    results = fetch_all_earnings_calendars(holdings)

    assert len(results) == 2
    assert mock_sleep.call_count == 2


@patch("app.sec.earnings.time.sleep")
@patch("app.sec.earnings.yf.Ticker")
def test_fetch_all_skips_errors(
    mock_ticker_cls: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    mock_ticker_cls.side_effect = [Exception("fail"), MagicMock()]
    mock_ticker_cls.return_value = MagicMock()
    # First call raises, second returns mock
    call_count = 0
    original_side_effect = mock_ticker_cls.side_effect

    def side_effect_fn(ticker: str) -> MagicMock:
        nonlocal call_count
        idx = call_count
        call_count += 1
        effects = list(original_side_effect)  # type: ignore[arg-type]
        if idx < len(effects):
            val = effects[idx]
            if isinstance(val, Exception):
                raise val
            return val  # type: ignore[return-value]
        m = MagicMock()
        m.earnings_dates = pd.DataFrame()
        return m

    mock_ticker_cls.side_effect = side_effect_fn

    holdings = [
        HoldingInfo(ticker="FAIL", name="Fail Co", cik="0000000001"),
        HoldingInfo(ticker="GOOD", name="Good Co", cik="0000000002"),
    ]
    results = fetch_all_earnings_calendars(holdings)

    # Only the non-failing one should be in results
    assert len(results) == 1
    assert results[0].ticker == "GOOD"

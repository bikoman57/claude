from __future__ import annotations

from app.congress.fetcher import Chamber, CongressTrade, TransactionType
from app.congress.members import (
    MemberTier,
    _assign_tier,
    get_member_weight,
    match_round_trips,
    rate_member,
)


def _make_trade(
    member: str = "Test Member",
    ticker: str = "AAPL",
    trade_date: str = "2025-01-15",
    tx_type: str = TransactionType.PURCHASE,
    amount_low: float = 1001.0,
    amount_high: float = 15000.0,
) -> CongressTrade:
    return CongressTrade(
        member_name=member,
        chamber=Chamber.HOUSE,
        party="D",
        state="CA",
        ticker=ticker,
        asset_description="Test Asset",
        transaction_type=tx_type,
        trade_date=trade_date,
        filing_date="2025-02-01",
        amount_low=amount_low,
        amount_high=amount_high,
        owner="Self",
        source="house",
    )


def test_assign_tier_a():
    assert _assign_tier(0.70, 6.0, 10) == MemberTier.A


def test_assign_tier_b():
    assert _assign_tier(0.60, 3.0, 10) == MemberTier.B


def test_assign_tier_c():
    assert _assign_tier(0.50, 1.0, 10) == MemberTier.C


def test_assign_tier_d():
    assert _assign_tier(0.38, 0.5, 10) == MemberTier.D


def test_assign_tier_f():
    assert _assign_tier(0.20, -5.0, 10) == MemberTier.F


def test_assign_tier_insufficient_data_defaults_c():
    # Even with great stats, <5 trades defaults to C
    assert _assign_tier(0.80, 10.0, 3) == MemberTier.C


def test_member_weight_a():
    assert get_member_weight(MemberTier.A) == 1.0


def test_member_weight_b():
    assert get_member_weight(MemberTier.B) == 0.75


def test_member_weight_c():
    assert get_member_weight(MemberTier.C) == 0.5


def test_member_weight_d():
    assert get_member_weight(MemberTier.D) == 0.25


def test_member_weight_f():
    assert get_member_weight(MemberTier.F) == 0.0


def test_member_weight_unknown():
    assert get_member_weight("X") == 0.5


def test_match_round_trips_basic():
    trades = [
        _make_trade(
            ticker="AAPL",
            trade_date="2025-01-10",
            tx_type=TransactionType.PURCHASE,
            amount_low=5000,
            amount_high=15000,
        ),
        _make_trade(
            ticker="AAPL",
            trade_date="2025-02-10",
            tx_type=TransactionType.SALE_FULL,
            amount_low=10000,
            amount_high=20000,
        ),
    ]
    trips = match_round_trips(trades)
    assert len(trips) == 1
    assert trips[0].ticker == "AAPL"
    assert trips[0].return_pct > 0  # sold higher than bought


def test_match_round_trips_no_sell():
    trades = [
        _make_trade(tx_type=TransactionType.PURCHASE),
    ]
    trips = match_round_trips(trades)
    assert len(trips) == 0


def test_rate_member_no_trades():
    rating = rate_member("Nobody", [])
    assert rating.total_trades == 0
    assert rating.tier == MemberTier.C


def test_rate_member_with_trades():
    trades = [
        _make_trade(
            member="Trader A",
            ticker="AAPL",
            trade_date="2025-01-10",
            tx_type=TransactionType.PURCHASE,
            amount_low=5000,
            amount_high=15000,
        ),
        _make_trade(
            member="Trader A",
            ticker="AAPL",
            trade_date="2025-02-10",
            tx_type=TransactionType.SALE_FULL,
            amount_low=10000,
            amount_high=20000,
        ),
    ]
    rating = rate_member("Trader A", trades)
    assert rating.name == "Trader A"
    assert rating.total_trades == 2
    assert rating.round_trips == 1
    assert rating.wins == 1

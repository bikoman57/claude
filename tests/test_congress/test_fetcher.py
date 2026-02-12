from __future__ import annotations

from app.congress.fetcher import (
    Chamber,
    CongressTrade,
    TransactionType,
    _deduplicate_trades,
    _normalize_transaction_type,
    _parse_amount_range,
)


def test_normalize_transaction_type_purchase():
    assert _normalize_transaction_type("purchase") == TransactionType.PURCHASE
    assert _normalize_transaction_type("Purchase") == TransactionType.PURCHASE


def test_normalize_transaction_type_sale_full():
    assert _normalize_transaction_type("sale_full") == TransactionType.SALE_FULL
    assert _normalize_transaction_type("Sale (Full)") == TransactionType.SALE_FULL


def test_normalize_transaction_type_sale_partial():
    assert _normalize_transaction_type("sale_partial") == TransactionType.SALE_PARTIAL
    assert _normalize_transaction_type("Sale (Partial)") == TransactionType.SALE_PARTIAL


def test_normalize_transaction_type_generic_sale():
    assert _normalize_transaction_type("sale") == TransactionType.SALE_PARTIAL


def test_normalize_transaction_type_exchange():
    assert _normalize_transaction_type("exchange") == TransactionType.EXCHANGE


def test_parse_amount_range_normal():
    low, high = _parse_amount_range("$1,001 - $15,000")
    assert low == 1001.0
    assert high == 15000.0


def test_parse_amount_range_over_1m():
    low, high = _parse_amount_range("$1,000,001 - $5,000,000")
    assert low == 1000001.0
    assert high == 5000000.0


def test_parse_amount_range_single_value():
    low, high = _parse_amount_range("$1,001 -")
    assert low == 1001.0
    assert high == 1001.0


def test_parse_amount_range_empty():
    assert _parse_amount_range("") == (0.0, 0.0)
    assert _parse_amount_range("--") == (0.0, 0.0)


def _make_trade(
    member: str = "Test Member",
    ticker: str = "AAPL",
    trade_date: str = "2025-01-15",
    tx_type: str = TransactionType.PURCHASE,
) -> CongressTrade:
    return CongressTrade(
        member_name=member,
        chamber=Chamber.HOUSE,
        party="D",
        state="CA",
        ticker=ticker,
        asset_description="Apple Inc.",
        transaction_type=tx_type,
        trade_date=trade_date,
        filing_date="2025-02-01",
        amount_low=1001.0,
        amount_high=15000.0,
        owner="Self",
        source="house",
    )


def test_deduplicate_trades_removes_duplicates():
    t1 = _make_trade()
    t2 = _make_trade()  # same key
    result = _deduplicate_trades([t1, t2])
    assert len(result) == 1


def test_deduplicate_trades_preserves_unique():
    t1 = _make_trade(ticker="AAPL")
    t2 = _make_trade(ticker="MSFT")
    t3 = _make_trade(member="Other Member")
    result = _deduplicate_trades([t1, t2, t3])
    assert len(result) == 3


def test_deduplicate_different_dates():
    t1 = _make_trade(trade_date="2025-01-15")
    t2 = _make_trade(trade_date="2025-01-16")
    result = _deduplicate_trades([t1, t2])
    assert len(result) == 2


def test_congress_trade_dataclass():
    t = _make_trade()
    assert t.member_name == "Test Member"
    assert t.chamber == Chamber.HOUSE
    assert t.ticker == "AAPL"
    assert t.transaction_type == TransactionType.PURCHASE

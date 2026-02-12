from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.congress.fetcher import Chamber, CongressTrade, TransactionType
from app.congress.members import MemberRating, MemberTier
from app.congress.sectors import (
    SectorSentiment,
    aggregate_sectors,
    compute_overall_sentiment,
    get_sector_sentiment_for_underlying,
    get_ticker_sector,
)


def test_ticker_to_sector_tech():
    assert get_ticker_sector("AAPL") == "tech"
    assert get_ticker_sector("MSFT") == "tech"
    assert get_ticker_sector("GOOGL") == "tech"


def test_ticker_to_sector_semiconductors():
    assert get_ticker_sector("NVDA") == "semiconductors"
    assert get_ticker_sector("AMD") == "semiconductors"


def test_ticker_to_sector_financials():
    assert get_ticker_sector("JPM") == "financials"
    assert get_ticker_sector("GS") == "financials"


def test_ticker_to_sector_biotech():
    assert get_ticker_sector("PFE") == "biotech"
    assert get_ticker_sector("LLY") == "biotech"


def test_ticker_to_sector_energy():
    assert get_ticker_sector("XOM") == "energy"
    assert get_ticker_sector("CVX") == "energy"


def test_ticker_to_sector_unknown():
    assert get_ticker_sector("ZZZZZ") is None


def _recent_date(days_ago: int = 5) -> str:
    return (datetime.now(tz=UTC) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _make_trade(
    member: str = "Test",
    ticker: str = "AAPL",
    tx_type: str = TransactionType.PURCHASE,
    days_ago: int = 5,
    amount_low: float = 50000.0,
    amount_high: float = 100000.0,
) -> CongressTrade:
    return CongressTrade(
        member_name=member,
        chamber=Chamber.HOUSE,
        party="D",
        state="CA",
        ticker=ticker,
        asset_description="Test",
        transaction_type=tx_type,
        trade_date=_recent_date(days_ago),
        filing_date=_recent_date(days_ago - 2),
        amount_low=amount_low,
        amount_high=amount_high,
        owner="Self",
        source="house",
    )


def _make_rating(
    name: str = "Test",
    tier: str = MemberTier.A,
) -> MemberRating:
    return MemberRating(
        name=name,
        chamber=Chamber.HOUSE,
        party="D",
        state="CA",
        total_trades=20,
        round_trips=10,
        wins=8,
        losses=2,
        win_rate=0.8,
        weighted_win_rate=0.8,
        avg_return_pct=5.0,
        tier=tier,
        trade_volume_usd=500000.0,
        last_trade_date=_recent_date(3),
        best_sectors=("AAPL", "MSFT"),
    )


def test_sector_aggregation_bullish():
    # Multiple big buys in tech with A-tier member
    trades = [
        _make_trade(member="Big Buyer", ticker="AAPL", amount_low=100000, amount_high=250000),
        _make_trade(member="Big Buyer", ticker="MSFT", amount_low=100000, amount_high=250000),
    ]
    ratings = [_make_rating(name="Big Buyer", tier=MemberTier.A)]
    sectors = aggregate_sectors(trades, ratings, sentiment_threshold=50000)

    tech = next(s for s in sectors if s.sector == "tech")
    assert tech.sentiment == SectorSentiment.BULLISH
    assert tech.buy_count == 2
    assert tech.underlying_ticker == "QQQ"
    assert tech.leveraged_ticker == "TQQQ"


def test_sector_aggregation_bearish():
    # Big sells in tech
    trades = [
        _make_trade(
            member="Seller",
            ticker="AAPL",
            tx_type=TransactionType.SALE_FULL,
            amount_low=100000,
            amount_high=250000,
        ),
        _make_trade(
            member="Seller",
            ticker="MSFT",
            tx_type=TransactionType.SALE_FULL,
            amount_low=100000,
            amount_high=250000,
        ),
    ]
    ratings = [_make_rating(name="Seller", tier=MemberTier.A)]
    sectors = aggregate_sectors(trades, ratings, sentiment_threshold=50000)

    tech = next(s for s in sectors if s.sector == "tech")
    assert tech.sentiment == SectorSentiment.BEARISH
    assert tech.sell_count == 2


def test_sector_aggregation_neutral_no_trades():
    sectors = aggregate_sectors([], None)
    for s in sectors:
        assert s.sentiment == SectorSentiment.NEUTRAL
        assert s.trade_count == 0


def test_member_weight_applied():
    # A-tier buy should outweigh F-tier buy
    trades_a = [_make_trade(member="A-Tier", ticker="AAPL", amount_low=50000, amount_high=100000)]
    ratings_a = [_make_rating(name="A-Tier", tier=MemberTier.A)]
    sectors_a = aggregate_sectors(trades_a, ratings_a)
    tech_a = next(s for s in sectors_a if s.sector == "tech")

    trades_f = [_make_trade(member="F-Tier", ticker="AAPL", amount_low=50000, amount_high=100000)]
    ratings_f = [_make_rating(name="F-Tier", tier=MemberTier.F)]
    sectors_f = aggregate_sectors(trades_f, ratings_f)
    tech_f = next(s for s in sectors_f if s.sector == "tech")

    assert tech_a.weighted_score > tech_f.weighted_score


def test_compute_overall_sentiment_bullish():
    from app.congress.sectors import SectorAggregation

    sectors = [
        SectorAggregation(
            sector="tech",
            underlying_ticker="QQQ",
            leveraged_ticker="TQQQ",
            net_buying_usd=200000.0,
            buy_count=10,
            sell_count=2,
            weighted_score=200000.0,
            sentiment=SectorSentiment.BULLISH,
            top_buyers=("Pelosi",),
            top_sellers=(),
            trade_count=12,
        ),
    ]
    assert compute_overall_sentiment(sectors) == SectorSentiment.BULLISH


def test_get_sector_sentiment_for_underlying():
    from app.congress.sectors import SectorAggregation

    sectors = [
        SectorAggregation(
            sector="tech",
            underlying_ticker="QQQ",
            leveraged_ticker="TQQQ",
            net_buying_usd=200000.0,
            buy_count=10,
            sell_count=2,
            weighted_score=200000.0,
            sentiment=SectorSentiment.BULLISH,
            top_buyers=(),
            top_sellers=(),
            trade_count=12,
        ),
    ]
    assert get_sector_sentiment_for_underlying(sectors, "QQQ") == SectorSentiment.BULLISH
    assert get_sector_sentiment_for_underlying(sectors, "XLF") == SectorSentiment.NEUTRAL

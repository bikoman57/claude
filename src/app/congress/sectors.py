"""Sector aggregation of Congress trades mapped to ETF universe."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.congress.fetcher import CongressTrade, TransactionType
from app.congress.members import MemberRating, get_member_weight

# Map individual stock tickers to sector categories
TICKER_SECTOR_MAP: dict[str, str] = {
    # Tech / QQQ / XLK
    "AAPL": "tech",
    "MSFT": "tech",
    "GOOGL": "tech",
    "GOOG": "tech",
    "AMZN": "tech",
    "META": "tech",
    "NFLX": "tech",
    "CRM": "tech",
    "ADBE": "tech",
    "ORCL": "tech",
    "CSCO": "tech",
    "IBM": "tech",
    "NOW": "tech",
    "UBER": "tech",
    "ABNB": "tech",
    "SNOW": "tech",
    "PLTR": "tech",
    "SHOP": "tech",
    # Semiconductors / SOXX
    "NVDA": "semiconductors",
    "AMD": "semiconductors",
    "AVGO": "semiconductors",
    "QCOM": "semiconductors",
    "TXN": "semiconductors",
    "MU": "semiconductors",
    "AMAT": "semiconductors",
    "LRCX": "semiconductors",
    "KLAC": "semiconductors",
    "INTC": "semiconductors",
    "MRVL": "semiconductors",
    "ON": "semiconductors",
    "TSM": "semiconductors",
    "ARM": "semiconductors",
    "ASML": "semiconductors",
    # Financials / XLF
    "JPM": "financials",
    "BAC": "financials",
    "WFC": "financials",
    "GS": "financials",
    "MS": "financials",
    "C": "financials",
    "BLK": "financials",
    "SCHW": "financials",
    "AXP": "financials",
    "USB": "financials",
    "PNC": "financials",
    "COF": "financials",
    "V": "financials",
    "MA": "financials",
    "PYPL": "financials",
    # Biotech/Healthcare / XBI
    "MRNA": "biotech",
    "PFE": "biotech",
    "JNJ": "biotech",
    "ABBV": "biotech",
    "LLY": "biotech",
    "AMGN": "biotech",
    "GILD": "biotech",
    "BIIB": "biotech",
    "REGN": "biotech",
    "BMY": "biotech",
    "UNH": "biotech",
    "TMO": "biotech",
    "ABT": "biotech",
    "VRTX": "biotech",
    "ISRG": "biotech",
    # Energy / USO
    "XOM": "energy",
    "CVX": "energy",
    "COP": "energy",
    "SLB": "energy",
    "EOG": "energy",
    "MPC": "energy",
    "OXY": "energy",
    "PSX": "energy",
    "VLO": "energy",
    "HAL": "energy",
    "DVN": "energy",
    "PXD": "energy",
    # Small Cap / IWM — broad small-cap names
    "ROKU": "small_cap",
    "ETSY": "small_cap",
    "DKNG": "small_cap",
    "PINS": "small_cap",
    "SNAP": "small_cap",
}

# Map sector categories to underlying ETF tickers from the universe
SECTOR_TO_UNDERLYING: dict[str, str] = {
    "tech": "QQQ",
    "semiconductors": "SOXX",
    "financials": "XLF",
    "biotech": "XBI",
    "energy": "USO",
    "broad_market": "SPY",
    "small_cap": "IWM",
}

# Reverse map: underlying ticker to leveraged ticker
UNDERLYING_TO_LEVERAGED: dict[str, str] = {
    "QQQ": "TQQQ",
    "SPY": "UPRO",
    "SOXX": "SOXL",
    "IWM": "TNA",
    "XLK": "TECL",
    "XLF": "FAS",
    "XBI": "LABU",
    "USO": "UCO",
}


class SectorSentiment(StrEnum):
    """Sector-level sentiment from Congress trades."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class SectorAggregation:
    """Aggregated Congress trading sentiment for one sector."""

    sector: str
    underlying_ticker: str
    leveraged_ticker: str
    net_buying_usd: float
    buy_count: int
    sell_count: int
    weighted_score: float
    sentiment: str  # SectorSentiment value
    top_buyers: tuple[str, ...]
    top_sellers: tuple[str, ...]
    trade_count: int


@dataclass(frozen=True, slots=True)
class CongressSummary:
    """Full Congress trading summary for chief-analyst integration."""

    total_trades: int
    trades_last_30d: int
    net_buying_usd: float
    overall_sentiment: str
    sectors: tuple[SectorAggregation, ...]
    top_members: tuple[str, ...]  # top member names by tier
    as_of: str


def _time_decay_weight(trade_date: str, window_days: int = 30) -> float:
    """Apply time decay: more recent trades weighted higher."""
    try:
        td = datetime.strptime(trade_date, "%Y-%m-%d").replace(tzinfo=UTC)
        days_ago = (datetime.now(tz=UTC) - td).days
    except ValueError:
        return 0.4

    if days_ago <= 7:
        return 1.0
    if days_ago <= 14:
        return 0.8
    if days_ago <= 21:
        return 0.6
    if days_ago <= window_days:
        return 0.4
    return 0.2


def get_ticker_sector(ticker: str) -> str | None:
    """Map a stock ticker to its sector category."""
    return TICKER_SECTOR_MAP.get(ticker.upper())


def aggregate_sectors(
    trades: list[CongressTrade],
    member_ratings: list[MemberRating] | None = None,
    *,
    days: int = 30,
    sentiment_threshold: float = 50_000.0,
) -> list[SectorAggregation]:
    """Aggregate Congress trades by sector, weighted by member tier.

    Args:
        trades: Recent Congress trades.
        member_ratings: Optional member ratings for weighting.
        days: Window of days to consider.
        sentiment_threshold: Dollar threshold for BULLISH/BEARISH.

    Returns:
        List of sector aggregations mapped to ETF universe.
    """
    # Build member tier lookup
    tier_lookup: dict[str, str] = {}
    if member_ratings:
        for r in member_ratings:
            tier_lookup[r.name] = r.tier

    # Filter by date window
    cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [t for t in trades if t.trade_date >= cutoff]

    # Aggregate by sector
    sector_buys: dict[str, float] = defaultdict(float)
    sector_sells: dict[str, float] = defaultdict(float)
    sector_buy_count: dict[str, int] = defaultdict(int)
    sector_sell_count: dict[str, int] = defaultdict(int)
    sector_buyers: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float),
    )
    sector_sellers: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float),
    )

    for trade in recent:
        sector = get_ticker_sector(trade.ticker)
        if sector is None:
            sector = "broad_market"

        mid = (trade.amount_low + trade.amount_high) / 2
        member_weight = get_member_weight(tier_lookup.get(trade.member_name, "C"))
        time_weight = _time_decay_weight(trade.trade_date, days)
        weighted_amount = mid * member_weight * time_weight

        is_buy = trade.transaction_type == TransactionType.PURCHASE
        if is_buy:
            sector_buys[sector] += weighted_amount
            sector_buy_count[sector] += 1
            sector_buyers[sector][trade.member_name] += weighted_amount
        else:
            sector_sells[sector] += weighted_amount
            sector_sell_count[sector] += 1
            sector_sellers[sector][trade.member_name] += weighted_amount

    # Build aggregations for each tracked sector
    results: list[SectorAggregation] = []
    for sector, underlying in SECTOR_TO_UNDERLYING.items():
        buys = sector_buys.get(sector, 0.0)
        sells = sector_sells.get(sector, 0.0)
        net = buys - sells
        score = net

        if score > sentiment_threshold:
            sentiment = SectorSentiment.BULLISH
        elif score < -sentiment_threshold:
            sentiment = SectorSentiment.BEARISH
        else:
            sentiment = SectorSentiment.NEUTRAL

        # Top 3 buyers/sellers by weighted volume
        buyers = sector_buyers.get(sector, {})
        sellers = sector_sellers.get(sector, {})
        top_b = sorted(buyers, key=buyers.get, reverse=True)[:3]  # type: ignore[arg-type]
        top_s = sorted(sellers, key=sellers.get, reverse=True)[:3]  # type: ignore[arg-type]

        leveraged = UNDERLYING_TO_LEVERAGED.get(underlying, "")

        results.append(
            SectorAggregation(
                sector=sector,
                underlying_ticker=underlying,
                leveraged_ticker=leveraged,
                net_buying_usd=round(net, 2),
                buy_count=sector_buy_count.get(sector, 0),
                sell_count=sector_sell_count.get(sector, 0),
                weighted_score=round(score, 2),
                sentiment=sentiment,
                top_buyers=tuple(top_b),
                top_sellers=tuple(top_s),
                trade_count=(
                    sector_buy_count.get(sector, 0) + sector_sell_count.get(sector, 0)
                ),
            ),
        )

    # Sort by absolute weighted score descending (most active sectors first)
    return sorted(results, key=lambda s: abs(s.weighted_score), reverse=True)


def compute_overall_sentiment(
    sectors: list[SectorAggregation],
) -> str:
    """Compute overall Congress sentiment across all sectors."""
    total_net = sum(s.net_buying_usd for s in sectors)
    if total_net > 100_000:
        return SectorSentiment.BULLISH
    if total_net < -100_000:
        return SectorSentiment.BEARISH
    return SectorSentiment.NEUTRAL


def get_sector_sentiment_for_underlying(
    sectors: list[SectorAggregation],
    underlying_ticker: str,
) -> str:
    """Get Congress sentiment for a specific underlying ETF ticker.

    Used by the confidence scoring system to assess Congress factor
    for a particular ETF signal.
    """
    for s in sectors:
        if s.underlying_ticker == underlying_ticker:
            return s.sentiment
    return SectorSentiment.NEUTRAL

"""Sector aggregation of Congress trades mapped to ETF universe."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.congress.fetcher import CongressTrade, TransactionType
from app.congress.members import MemberRating, get_member_weight
from app.sec.holdings import INDEX_HOLDINGS

# Map underlying ETF → sector name (used to build ticker→sector map)
_UNDERLYING_TO_SECTOR: dict[str, str] = {
    "QQQ": "tech",
    "SOXX": "semiconductors",
    "XLF": "financials",
    "XBI": "biotech",
    "XLE": "energy",
    "IWM": "small_cap",
    # SPY and XLK are broad/overlap — handled by priority below
}

# Priority: more-specific index wins for stocks in multiple indices.
# Lower number = higher priority (checked first).
_INDEX_PRIORITY: tuple[str, ...] = (
    "SOXX",  # semiconductor-specific
    "XLE",  # energy-specific
    "XBI",  # biotech-specific
    "XLF",  # financials-specific
    "IWM",  # small-cap-specific
    "QQQ",  # broad tech (catches remaining tech names)
    "XLK",  # tech select (subset of QQQ mostly)
    "SPY",  # broadest — fallback
)

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


def _build_ticker_map() -> dict[str, str]:
    """Build ticker→sector map from SEC index holdings.

    Uses index priority so more-specific indices win for stocks
    that appear in multiple indices (e.g. NVDA → semiconductors, not tech).
    """
    result: dict[str, str] = {}
    for index in _INDEX_PRIORITY:
        sector = _UNDERLYING_TO_SECTOR.get(index)
        if sector is None:
            continue
        for holding in INDEX_HOLDINGS.get(index, []):
            if holding.ticker not in result:
                result[holding.ticker] = sector
    return result


# Built once at import time from the SEC holdings data
TICKER_SECTOR_MAP: dict[str, str] = _build_ticker_map()


class SectorSentiment(StrEnum):
    """Sector-level sentiment from Congress trades."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class TickerDetail:
    """Per-ticker trade detail within a sector."""

    ticker: str
    trade_count: int
    net_usd: float


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
    top_tickers: tuple[TickerDetail, ...] = ()


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
    # Per-ticker tracking within each sector
    ticker_buys: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float),
    )
    ticker_sells: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float),
    )
    ticker_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int),
    )

    for trade in recent:
        sector = get_ticker_sector(trade.ticker)
        if sector is None:
            sector = "broad_market"

        mid = (trade.amount_low + trade.amount_high) / 2
        member_weight = get_member_weight(
            tier_lookup.get(trade.member_name, "C"),
        )
        time_weight = _time_decay_weight(trade.trade_date, days)
        weighted_amount = mid * member_weight * time_weight

        is_buy = trade.transaction_type == TransactionType.PURCHASE
        ticker_counts[sector][trade.ticker] += 1
        if is_buy:
            sector_buys[sector] += weighted_amount
            sector_buy_count[sector] += 1
            sector_buyers[sector][trade.member_name] += weighted_amount
            ticker_buys[sector][trade.ticker] += weighted_amount
        else:
            sector_sells[sector] += weighted_amount
            sector_sell_count[sector] += 1
            sector_sellers[sector][trade.member_name] += weighted_amount
            ticker_sells[sector][trade.ticker] += weighted_amount

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

        # Top tickers by trade count (max 5)
        sec_tickers = ticker_counts.get(sector, {})
        sec_buys = ticker_buys.get(sector, {})
        sec_sells = ticker_sells.get(sector, {})
        sorted_tickers = sorted(
            sec_tickers.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        top_ticker_details = tuple(
            TickerDetail(
                ticker=tk,
                trade_count=cnt,
                net_usd=round(
                    sec_buys.get(tk, 0.0) - sec_sells.get(tk, 0.0),
                    2,
                ),
            )
            for tk, cnt in sorted_tickers
        )

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
                top_tickers=top_ticker_details,
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

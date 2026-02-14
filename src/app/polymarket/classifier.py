"""Polymarket classifier: categorize and score prediction markets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.polymarket.fetcher import PolymarketMarket


class MarketCategory(StrEnum):
    """Category of a prediction market relevant to our trading system."""

    FED_POLICY = "FED_POLICY"
    RECESSION = "RECESSION"
    TARIFF_TRADE = "TARIFF_TRADE"
    GEOPOLITICAL = "GEOPOLITICAL"
    ELECTION = "ELECTION"
    ECONOMIC_INDICATOR = "ECONOMIC_INDICATOR"
    MARKET_EVENT = "MARKET_EVENT"


class MarketSignal(StrEnum):
    """Directional signal from a prediction market."""

    FAVORABLE = "FAVORABLE"
    UNFAVORABLE = "UNFAVORABLE"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class TrackedQuery:
    """A keyword pattern to search for in Polymarket events."""

    keywords: tuple[str, ...]
    category: MarketCategory
    sectors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClassifiedMarket:
    """A prediction market classified for our trading system."""

    market_id: str
    question: str
    category: MarketCategory
    signal: MarketSignal
    probability: float
    affected_sectors: tuple[str, ...]
    reason: str
    volume: float


@dataclass(frozen=True, slots=True)
class PredictionSummary:
    """Aggregated prediction market summary."""

    total_markets: int
    relevant_markets: int
    overall_signal: str
    favorable_count: int
    unfavorable_count: int
    neutral_count: int
    markets_by_category: dict[str, int]
    affected_sectors: dict[str, str]
    top_markets: tuple[ClassifiedMarket, ...]
    as_of: str


TRACKED_QUERIES: list[TrackedQuery] = [
    TrackedQuery(
        keywords=(
            "fed", "federal reserve", "rate cut", "rate hike", "fomc",
            "interest rate", "monetary policy", "powell",
        ),
        category=MarketCategory.FED_POLICY,
        sectors=("broad_market", "tech", "financials"),
    ),
    TrackedQuery(
        keywords=(
            "recession", "gdp", "economic contraction", "soft landing",
            "hard landing", "unemployment rate",
        ),
        category=MarketCategory.RECESSION,
        sectors=("broad_market",),
    ),
    TrackedQuery(
        keywords=(
            "tariff", "trade war", "trade deal", "import tax",
            "trade policy", "customs duty",
        ),
        category=MarketCategory.TARIFF_TRADE,
        sectors=("tech", "semiconductors"),
    ),
    TrackedQuery(
        keywords=(
            "china", "taiwan", "russia", "ukraine", "iran", "sanctions",
            "military", "invasion", "conflict",
        ),
        category=MarketCategory.GEOPOLITICAL,
        sectors=("energy", "semiconductors"),
    ),
    TrackedQuery(
        keywords=(
            "election", "congress", "senate", "house majority",
            "president", "governor", "midterm",
        ),
        category=MarketCategory.ELECTION,
        sectors=("broad_market", "financials"),
    ),
    TrackedQuery(
        keywords=(
            "cpi", "inflation", "jobs report", "nonfarm", "pce",
            "consumer price", "core inflation",
        ),
        category=MarketCategory.ECONOMIC_INDICATOR,
        sectors=("broad_market",),
    ),
    TrackedQuery(
        keywords=(
            "s&p 500", "nasdaq", "stock market", "ipo",
            "market crash", "bear market", "correction", "dow jones",
        ),
        category=MarketCategory.MARKET_EVENT,
        sectors=("broad_market", "tech"),
    ),
]

# Keywords that invert signal (YES = bad for markets)
_UNFAVORABLE_KEYWORDS = (
    "recession", "contraction", "crash", "bear market", "conflict",
    "war", "invasion", "sanctions", "tariff", "trade war", "hike",
    "rate hike", "raise rates", "hawkish",
)

# Keywords that are favorable (YES = good for markets)
_FAVORABLE_KEYWORDS = (
    "rate cut", "cut rates", "lower rates", "easing", "dovish",
    "soft landing", "deal", "peace", "ceasefire", "rally",
)


def classify_market(
    market: PolymarketMarket,
    query: TrackedQuery,
) -> ClassifiedMarket:
    """Classify a market's signal based on its category and probability."""
    # Get YES price (first outcome)
    yes_price = market.outcome_prices[0] if market.outcome_prices else 0.5
    question_lower = market.question.lower()

    signal = MarketSignal.NEUTRAL
    reason = f"{yes_price:.0%} probability"

    # Check for favorable keywords first
    is_favorable_event = any(kw in question_lower for kw in _FAVORABLE_KEYWORDS)
    is_unfavorable_event = any(kw in question_lower for kw in _UNFAVORABLE_KEYWORDS)

    if query.category == MarketCategory.FED_POLICY:
        if is_favorable_event and yes_price > 0.60:
            signal = MarketSignal.FAVORABLE
            reason = f"Rate cut/easing {yes_price:.0%} likely — supports entry"
        elif is_unfavorable_event and yes_price > 0.60:
            signal = MarketSignal.UNFAVORABLE
            reason = f"Rate hike/hawkish {yes_price:.0%} likely — opposes entry"
        elif yes_price > 0.60:
            # Generic Fed question — slight caution
            signal = MarketSignal.NEUTRAL
            reason = f"Fed policy event {yes_price:.0%} — monitoring"

    elif query.category == MarketCategory.RECESSION:
        if is_unfavorable_event:
            if yes_price > 0.80:
                # Contrarian: extreme pricing = already reflected
                signal = MarketSignal.FAVORABLE
                reason = f"Recession {yes_price:.0%} priced — contrarian opportunity"
            elif yes_price > 0.50:
                signal = MarketSignal.UNFAVORABLE
                reason = f"Recession {yes_price:.0%} likely — risk elevated"

    elif query.category == MarketCategory.TARIFF_TRADE:
        if is_unfavorable_event and yes_price > 0.60:
            signal = MarketSignal.UNFAVORABLE
            reason = f"Tariff/trade war {yes_price:.0%} likely — tech/semis risk"
        elif is_favorable_event and yes_price > 0.60:
            signal = MarketSignal.FAVORABLE
            reason = f"Trade deal {yes_price:.0%} likely — positive for tech/semis"

    elif query.category == MarketCategory.GEOPOLITICAL:
        if is_unfavorable_event and yes_price > 0.50:
            signal = MarketSignal.UNFAVORABLE
            reason = f"Geopolitical risk {yes_price:.0%} — energy/semis exposure"
        elif is_favorable_event and yes_price > 0.60:
            signal = MarketSignal.FAVORABLE
            reason = f"Geopolitical de-escalation {yes_price:.0%} likely"

    elif query.category == MarketCategory.ELECTION:
        # Elections are complex — default neutral unless strong signal
        if yes_price > 0.85:
            signal = MarketSignal.NEUTRAL
            reason = f"Election outcome {yes_price:.0%} — high certainty, priced in"

    elif query.category == MarketCategory.ECONOMIC_INDICATOR:
        if is_unfavorable_event and yes_price > 0.60:
            signal = MarketSignal.UNFAVORABLE
            reason = f"Negative economic indicator {yes_price:.0%} likely"
        elif is_favorable_event and yes_price > 0.60:
            signal = MarketSignal.FAVORABLE
            reason = f"Positive economic indicator {yes_price:.0%} likely"

    elif query.category == MarketCategory.MARKET_EVENT:
        if is_unfavorable_event and yes_price > 0.50:
            signal = MarketSignal.UNFAVORABLE
            reason = f"Market downturn {yes_price:.0%} likely"
        elif is_unfavorable_event and yes_price < 0.20:
            signal = MarketSignal.FAVORABLE
            reason = f"Market crash unlikely ({yes_price:.0%}) — supportive"

    return ClassifiedMarket(
        market_id=market.market_id,
        question=market.question,
        category=query.category,
        signal=signal,
        probability=yes_price,
        affected_sectors=query.sectors,
        reason=reason,
        volume=market.volume,
    )


def _compute_sector_signals(
    markets: list[ClassifiedMarket],
) -> dict[str, str]:
    """Compute per-sector signal from classified markets via volume-weighted vote."""
    sector_favorable: dict[str, float] = defaultdict(float)
    sector_unfavorable: dict[str, float] = defaultdict(float)

    for m in markets:
        weight = min(m.volume, 1_000_000) / 1_000_000
        for sector in m.affected_sectors:
            if m.signal == MarketSignal.FAVORABLE:
                sector_favorable[sector] += weight
            elif m.signal == MarketSignal.UNFAVORABLE:
                sector_unfavorable[sector] += weight

    result: dict[str, str] = {}
    all_sectors = set(sector_favorable) | set(sector_unfavorable)
    for sector in sorted(all_sectors):
        fav = sector_favorable.get(sector, 0)
        unfav = sector_unfavorable.get(sector, 0)
        if fav > unfav * 1.5:
            result[sector] = MarketSignal.FAVORABLE
        elif unfav > fav * 1.5:
            result[sector] = MarketSignal.UNFAVORABLE
        else:
            result[sector] = MarketSignal.NEUTRAL

    return result


def build_prediction_summary(
    markets: list[ClassifiedMarket],
    top_n: int = 10,
) -> PredictionSummary:
    """Build aggregated prediction market summary."""
    favorable = sum(1 for m in markets if m.signal == MarketSignal.FAVORABLE)
    unfavorable = sum(1 for m in markets if m.signal == MarketSignal.UNFAVORABLE)
    neutral = sum(1 for m in markets if m.signal == MarketSignal.NEUTRAL)

    # Category breakdown
    cat_counts: dict[str, int] = {}
    for m in markets:
        cat_counts[m.category] = cat_counts.get(m.category, 0) + 1

    # Per-sector signals
    sector_signals = _compute_sector_signals(markets)

    # Overall signal
    if favorable > unfavorable * 1.5:
        overall = MarketSignal.FAVORABLE
    elif unfavorable > favorable * 1.5:
        overall = MarketSignal.UNFAVORABLE
    else:
        overall = MarketSignal.NEUTRAL

    # Top markets by volume
    sorted_markets = sorted(markets, key=lambda m: m.volume, reverse=True)

    return PredictionSummary(
        total_markets=len(markets),
        relevant_markets=sum(1 for m in markets if m.signal != MarketSignal.NEUTRAL),
        overall_signal=overall,
        favorable_count=favorable,
        unfavorable_count=unfavorable,
        neutral_count=neutral,
        markets_by_category=cat_counts,
        affected_sectors=sector_signals,
        top_markets=tuple(sorted_markets[:top_n]),
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )

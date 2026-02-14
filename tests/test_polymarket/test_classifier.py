"""Tests for Polymarket classifier module."""

from __future__ import annotations

from app.polymarket.classifier import (
    ClassifiedMarket,
    MarketCategory,
    MarketSignal,
    TrackedQuery,
    build_prediction_summary,
    classify_market,
)
from app.polymarket.fetcher import PolymarketMarket


def _make_market(
    question: str = "Test market?",
    yes_price: float = 0.5,
    volume: float = 100_000,
    **kwargs: object,
) -> PolymarketMarket:
    """Helper to create a test market."""
    return PolymarketMarket(
        market_id=str(kwargs.get("market_id", "test-1")),
        question=question,
        slug="test",
        outcomes=("Yes", "No"),
        outcome_prices=(yes_price, round(1 - yes_price, 4)),
        volume=volume,
        liquidity=float(kwargs.get("liquidity", 50_000)),
        end_date="2026-12-31",
        active=True,
        event_slug="test-event",
        event_title=str(kwargs.get("event_title", "Test Event")),
        tags=(),
    )


_FED_QUERY = TrackedQuery(
    keywords=("fed", "rate cut", "rate hike"),
    category=MarketCategory.FED_POLICY,
    sectors=("broad_market", "tech", "financials"),
)

_RECESSION_QUERY = TrackedQuery(
    keywords=("recession",),
    category=MarketCategory.RECESSION,
    sectors=("broad_market",),
)

_TARIFF_QUERY = TrackedQuery(
    keywords=("tariff", "trade war"),
    category=MarketCategory.TARIFF_TRADE,
    sectors=("tech", "semiconductors"),
)

_GEO_QUERY = TrackedQuery(
    keywords=("conflict", "war", "invasion"),
    category=MarketCategory.GEOPOLITICAL,
    sectors=("energy", "semiconductors"),
)

_MARKET_QUERY = TrackedQuery(
    keywords=("market crash", "bear market"),
    category=MarketCategory.MARKET_EVENT,
    sectors=("broad_market", "tech"),
)


class TestClassifyFedPolicy:
    def test_rate_cut_favorable(self):
        market = _make_market("Will the Fed cut rates in March?", yes_price=0.72)
        result = classify_market(market, _FED_QUERY)
        assert result.signal == MarketSignal.FAVORABLE
        assert result.category == MarketCategory.FED_POLICY
        assert "rate cut" in result.reason.lower() or "easing" in result.reason.lower()

    def test_rate_hike_unfavorable(self):
        market = _make_market("Will the Fed raise rates?", yes_price=0.75)
        result = classify_market(market, _FED_QUERY)
        assert result.signal == MarketSignal.UNFAVORABLE

    def test_low_probability_neutral(self):
        market = _make_market("Will the Fed cut rates?", yes_price=0.40)
        result = classify_market(market, _FED_QUERY)
        assert result.signal == MarketSignal.NEUTRAL


class TestClassifyRecession:
    def test_recession_likely_unfavorable(self):
        market = _make_market("Will there be a recession in 2026?", yes_price=0.65)
        result = classify_market(market, _RECESSION_QUERY)
        assert result.signal == MarketSignal.UNFAVORABLE

    def test_recession_extreme_contrarian(self):
        market = _make_market("Will there be a recession in 2026?", yes_price=0.85)
        result = classify_market(market, _RECESSION_QUERY)
        assert result.signal == MarketSignal.FAVORABLE
        assert "contrarian" in result.reason.lower()

    def test_recession_low_probability_neutral(self):
        market = _make_market("Will there be a recession in 2026?", yes_price=0.30)
        result = classify_market(market, _RECESSION_QUERY)
        assert result.signal == MarketSignal.NEUTRAL


class TestClassifyTariff:
    def test_tariff_unfavorable(self):
        market = _make_market("Will new tariffs be imposed on China?", yes_price=0.70)
        result = classify_market(market, _TARIFF_QUERY)
        assert result.signal == MarketSignal.UNFAVORABLE
        assert result.affected_sectors == ("tech", "semiconductors")

    def test_trade_deal_favorable(self):
        market = _make_market("Will a trade deal be reached?", yes_price=0.75)
        result = classify_market(market, _TARIFF_QUERY)
        assert result.signal == MarketSignal.FAVORABLE


class TestClassifyGeopolitical:
    def test_conflict_unfavorable(self):
        market = _make_market(
            "Will there be a military conflict in Taiwan?", yes_price=0.55,
        )
        result = classify_market(market, _GEO_QUERY)
        assert result.signal == MarketSignal.UNFAVORABLE

    def test_ceasefire_favorable(self):
        market = _make_market("Will a ceasefire be reached?", yes_price=0.70)
        result = classify_market(market, _GEO_QUERY)
        assert result.signal == MarketSignal.FAVORABLE

    def test_low_conflict_neutral(self):
        market = _make_market("Will there be a conflict?", yes_price=0.20)
        result = classify_market(market, _GEO_QUERY)
        assert result.signal == MarketSignal.NEUTRAL


class TestClassifyMarketEvent:
    def test_crash_unfavorable(self):
        market = _make_market("Will there be a market crash?", yes_price=0.55)
        result = classify_market(market, _MARKET_QUERY)
        assert result.signal == MarketSignal.UNFAVORABLE

    def test_crash_unlikely_favorable(self):
        market = _make_market("Will there be a market crash?", yes_price=0.10)
        result = classify_market(market, _MARKET_QUERY)
        assert result.signal == MarketSignal.FAVORABLE


class TestBuildPredictionSummary:
    def _make_classified(
        self,
        signal: MarketSignal,
        category: MarketCategory = MarketCategory.FED_POLICY,
        volume: float = 100_000,
        market_id: str = "1",
    ) -> ClassifiedMarket:
        return ClassifiedMarket(
            market_id=market_id,
            question="Test?",
            category=category,
            signal=signal,
            probability=0.6,
            affected_sectors=("broad_market",),
            reason="test",
            volume=volume,
        )

    def test_overall_favorable(self):
        markets = [
            self._make_classified(MarketSignal.FAVORABLE, market_id="1"),
            self._make_classified(MarketSignal.FAVORABLE, market_id="2"),
            self._make_classified(MarketSignal.FAVORABLE, market_id="3"),
            self._make_classified(MarketSignal.NEUTRAL, market_id="4"),
        ]
        summary = build_prediction_summary(markets)
        assert summary.overall_signal == MarketSignal.FAVORABLE
        assert summary.favorable_count == 3
        assert summary.neutral_count == 1
        assert summary.total_markets == 4

    def test_overall_unfavorable(self):
        markets = [
            self._make_classified(MarketSignal.UNFAVORABLE, market_id="1"),
            self._make_classified(MarketSignal.UNFAVORABLE, market_id="2"),
            self._make_classified(MarketSignal.UNFAVORABLE, market_id="3"),
            self._make_classified(MarketSignal.NEUTRAL, market_id="4"),
        ]
        summary = build_prediction_summary(markets)
        assert summary.overall_signal == MarketSignal.UNFAVORABLE

    def test_overall_neutral_when_mixed(self):
        markets = [
            self._make_classified(MarketSignal.FAVORABLE, market_id="1"),
            self._make_classified(MarketSignal.UNFAVORABLE, market_id="2"),
        ]
        summary = build_prediction_summary(markets)
        assert summary.overall_signal == MarketSignal.NEUTRAL

    def test_empty_markets(self):
        summary = build_prediction_summary([])
        assert summary.total_markets == 0
        assert summary.overall_signal == MarketSignal.NEUTRAL

    def test_top_markets_sorted_by_volume(self):
        markets = [
            self._make_classified(MarketSignal.FAVORABLE, volume=100, market_id="1"),
            self._make_classified(
                MarketSignal.FAVORABLE, volume=999_999, market_id="2",
            ),
            self._make_classified(MarketSignal.UNFAVORABLE, volume=500, market_id="3"),
        ]
        summary = build_prediction_summary(markets, top_n=2)
        assert len(summary.top_markets) == 2
        assert summary.top_markets[0].volume == 999_999

    def test_category_breakdown(self):
        markets = [
            self._make_classified(
                MarketSignal.FAVORABLE,
                category=MarketCategory.FED_POLICY,
                market_id="1",
            ),
            self._make_classified(
                MarketSignal.UNFAVORABLE,
                category=MarketCategory.RECESSION,
                market_id="2",
            ),
            self._make_classified(
                MarketSignal.FAVORABLE,
                category=MarketCategory.FED_POLICY,
                market_id="3",
            ),
        ]
        summary = build_prediction_summary(markets)
        assert summary.markets_by_category["FED_POLICY"] == 2
        assert summary.markets_by_category["RECESSION"] == 1

    def test_sector_signals(self):
        markets = [
            ClassifiedMarket(
                market_id="1",
                question="Rate cut?",
                category=MarketCategory.FED_POLICY,
                signal=MarketSignal.FAVORABLE,
                probability=0.7,
                affected_sectors=("tech", "broad_market"),
                reason="test",
                volume=500_000,
            ),
            ClassifiedMarket(
                market_id="2",
                question="Rate cut 2?",
                category=MarketCategory.FED_POLICY,
                signal=MarketSignal.FAVORABLE,
                probability=0.7,
                affected_sectors=("tech",),
                reason="test",
                volume=500_000,
            ),
        ]
        summary = build_prediction_summary(markets)
        assert summary.affected_sectors.get("tech") == MarketSignal.FAVORABLE

    def test_relevant_markets_excludes_neutral(self):
        markets = [
            self._make_classified(MarketSignal.FAVORABLE, market_id="1"),
            self._make_classified(MarketSignal.NEUTRAL, market_id="2"),
            self._make_classified(MarketSignal.UNFAVORABLE, market_id="3"),
        ]
        summary = build_prediction_summary(markets)
        assert summary.relevant_markets == 2  # Excludes neutral

"""Tests for Polymarket fetcher module."""

from __future__ import annotations

from app.polymarket.fetcher import PolymarketMarket, _match_keywords, _parse_market


class TestMatchKeywords:
    def test_exact_match(self):
        assert _match_keywords("Federal Reserve meeting", ("federal reserve",))

    def test_case_insensitive(self):
        assert _match_keywords("FEDERAL RESERVE", ("federal reserve",))

    def test_partial_match(self):
        assert _match_keywords("Will the Fed cut rates?", ("fed",))

    def test_no_match(self):
        assert not _match_keywords(
            "Sports betting market", ("federal reserve", "tariff"),
        )

    def test_multiple_keywords_any_match(self):
        assert _match_keywords("New tariff announced", ("fed", "tariff", "recession"))

    def test_empty_text(self):
        assert not _match_keywords("", ("fed",))

    def test_empty_keywords(self):
        assert not _match_keywords("Some text", ())


class TestParseMarket:
    def _make_event(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "slug": "test-event",
            "title": "Test Event",
            "tags": [{"label": "Politics"}],
        }
        base.update(overrides)
        return base

    def _make_market(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "id": "market-123",
            "question": "Will the Fed cut rates?",
            "slug": "fed-cut-rates",
            "active": True,
            "endDate": "2026-12-31",
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '[0.65, 0.35]',
            "volume": 500000,
            "liquidity": 100000,
        }
        base.update(overrides)
        return base

    def test_parse_valid_market(self):
        event = self._make_event()
        market = self._make_market()
        result = _parse_market(market, event)

        assert result is not None
        assert result.market_id == "market-123"
        assert result.question == "Will the Fed cut rates?"
        assert result.outcomes == ("Yes", "No")
        assert result.outcome_prices == (0.65, 0.35)
        assert result.volume == 500000
        assert result.liquidity == 100000
        assert result.event_title == "Test Event"
        assert result.tags == ("Politics",)

    def test_parse_missing_id(self):
        event = self._make_event()
        market = self._make_market(id="")
        result = _parse_market(market, event)
        assert result is None

    def test_parse_missing_question(self):
        event = self._make_event()
        market = self._make_market(question="")
        result = _parse_market(market, event)
        assert result is None

    def test_parse_outcomes_as_list(self):
        event = self._make_event()
        market = self._make_market(outcomes=["Yes", "No"], outcomePrices=[0.7, 0.3])
        result = _parse_market(market, event)
        assert result is not None
        assert result.outcomes == ("Yes", "No")
        assert result.outcome_prices == (0.7, 0.3)

    def test_parse_missing_outcomes(self):
        event = self._make_event()
        market = self._make_market(outcomes="", outcomePrices="")
        result = _parse_market(market, event)
        assert result is not None
        assert result.outcomes == ()
        assert result.outcome_prices == ()

    def test_parse_zero_volume(self):
        event = self._make_event()
        market = self._make_market(volume=0, liquidity=0)
        result = _parse_market(market, event)
        assert result is not None
        assert result.volume == 0
        assert result.liquidity == 0

    def test_parse_tags_as_strings(self):
        event = self._make_event(tags=["Politics", "Economics"])
        market = self._make_market()
        result = _parse_market(market, event)
        assert result is not None
        assert result.tags == ("Politics", "Economics")

    def test_parse_no_tags(self):
        event = self._make_event(tags=[])
        market = self._make_market()
        result = _parse_market(market, event)
        assert result is not None
        assert result.tags == ()


class TestPolymarketMarketFrozen:
    def test_immutable(self):
        market = PolymarketMarket(
            market_id="1",
            question="Test?",
            slug="test",
            outcomes=("Yes", "No"),
            outcome_prices=(0.5, 0.5),
            volume=1000,
            liquidity=500,
            end_date="2026-12-31",
            active=True,
            event_slug="ev",
            event_title="Event",
            tags=(),
        )
        try:
            market.volume = 999  # type: ignore[misc]
            raise AssertionError("Should not allow mutation")
        except AttributeError:
            pass  # Expected — frozen dataclass

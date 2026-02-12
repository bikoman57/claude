from __future__ import annotations

from app.etf.confidence import (
    ConfidenceLevel,
    FactorAssessment,
    FactorResult,
    assess_congress_sentiment,
    assess_drawdown_depth,
    assess_fed_regime,
    assess_geopolitical_risk,
    assess_market_statistics,
    assess_news_sentiment,
    assess_social_sentiment,
    assess_vix_regime,
    assess_yield_curve,
    compute_confidence,
)


def test_individual_assessments():
    # Drawdown
    r = assess_drawdown_depth(-0.10, 0.05)
    assert r.assessment == FactorAssessment.FAVORABLE
    r = assess_drawdown_depth(-0.05, 0.05)
    assert r.assessment == FactorAssessment.NEUTRAL
    r = assess_drawdown_depth(-0.02, 0.05)
    assert r.assessment == FactorAssessment.UNFAVORABLE

    # VIX
    assert assess_vix_regime("ELEVATED").assessment == FactorAssessment.FAVORABLE
    assert assess_vix_regime("NORMAL").assessment == FactorAssessment.NEUTRAL
    assert assess_vix_regime("LOW").assessment == FactorAssessment.UNFAVORABLE

    # Fed
    assert assess_fed_regime("CUTTING").assessment == FactorAssessment.FAVORABLE
    assert assess_fed_regime("PAUSING").assessment == FactorAssessment.NEUTRAL
    assert assess_fed_regime("HIKING").assessment == FactorAssessment.UNFAVORABLE

    # Yield curve
    assert assess_yield_curve("NORMAL").assessment == FactorAssessment.FAVORABLE
    assert assess_yield_curve("FLAT").assessment == FactorAssessment.NEUTRAL
    assert assess_yield_curve("INVERTED").assessment == FactorAssessment.UNFAVORABLE


def _fav(name: str) -> FactorResult:
    return FactorResult(name, FactorAssessment.FAVORABLE, "test")


def _unfav(name: str) -> FactorResult:
    return FactorResult(name, FactorAssessment.UNFAVORABLE, "test")


def _neutral(name: str) -> FactorResult:
    return FactorResult(name, FactorAssessment.NEUTRAL, "test")


def test_new_factor_geopolitical():
    r = assess_geopolitical_risk("LOW")
    assert r.assessment == FactorAssessment.FAVORABLE
    r = assess_geopolitical_risk("MEDIUM")
    assert r.assessment == FactorAssessment.NEUTRAL
    r = assess_geopolitical_risk("HIGH")
    assert r.assessment == FactorAssessment.UNFAVORABLE


def test_new_factor_social_sentiment():
    r = assess_social_sentiment("BEARISH")
    assert r.assessment == FactorAssessment.FAVORABLE
    r = assess_social_sentiment("BULLISH")
    assert r.assessment == FactorAssessment.NEUTRAL
    r = assess_social_sentiment("NEUTRAL")
    assert r.assessment == FactorAssessment.NEUTRAL


def test_new_factor_news_sentiment():
    r = assess_news_sentiment("BEARISH")
    assert r.assessment == FactorAssessment.FAVORABLE
    r = assess_news_sentiment("BULLISH")
    assert r.assessment == FactorAssessment.NEUTRAL
    r = assess_news_sentiment("NEUTRAL")
    assert r.assessment == FactorAssessment.NEUTRAL


def test_new_factor_market_statistics():
    r = assess_market_statistics("RISK_OFF")
    assert r.assessment == FactorAssessment.FAVORABLE
    r = assess_market_statistics("RISK_ON")
    assert r.assessment == FactorAssessment.NEUTRAL
    r = assess_market_statistics("NEUTRAL")
    assert r.assessment == FactorAssessment.NEUTRAL


def test_congress_sentiment_bullish():
    # NOT contrarian: buying = FAVORABLE
    r = assess_congress_sentiment("BULLISH")
    assert r.assessment == FactorAssessment.FAVORABLE
    assert r.name == "congress_sentiment"


def test_congress_sentiment_bearish():
    r = assess_congress_sentiment("BEARISH")
    assert r.assessment == FactorAssessment.UNFAVORABLE


def test_congress_sentiment_neutral():
    r = assess_congress_sentiment("NEUTRAL")
    assert r.assessment == FactorAssessment.NEUTRAL


def test_compute_confidence_high():
    # 10-factor system: HIGH requires 8+
    factors = [_fav(f"f{i}") for i in range(8)] + [
        _neutral("n1"),
        _neutral("n2"),
    ]
    score = compute_confidence(factors)
    assert score.level == ConfidenceLevel.HIGH
    assert score.favorable_count == 8


def test_compute_confidence_medium():
    # 10-factor system: MEDIUM is 5-7
    factors = [_fav(f"f{i}") for i in range(6)] + [_neutral(f"n{i}") for i in range(4)]
    score = compute_confidence(factors)
    assert score.level == ConfidenceLevel.MEDIUM
    assert score.favorable_count == 6


def test_compute_confidence_low():
    # 10-factor system: LOW is 0-4
    factors = (
        [_fav("f1")]
        + [_unfav(f"u{i}") for i in range(5)]
        + [_neutral(f"n{i}") for i in range(4)]
    )
    score = compute_confidence(factors)
    assert score.level == ConfidenceLevel.LOW
    assert score.favorable_count == 1

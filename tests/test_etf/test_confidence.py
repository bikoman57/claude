from __future__ import annotations

from app.etf.confidence import (
    ConfidenceLevel,
    FactorAssessment,
    FactorResult,
    assess_drawdown_depth,
    assess_fed_regime,
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


def test_compute_confidence_high():
    factors = [_fav("a"), _fav("b"), _fav("c"), _fav("d"), _neutral("e")]
    score = compute_confidence(factors)
    assert score.level == ConfidenceLevel.HIGH
    assert score.favorable_count == 4


def test_compute_confidence_medium():
    factors = [_fav("a"), _fav("b"), _neutral("c"), _unfav("d"), _unfav("e")]
    score = compute_confidence(factors)
    assert score.level == ConfidenceLevel.MEDIUM
    assert score.favorable_count == 2


def test_compute_confidence_low():
    factors = [_unfav("a"), _unfav("b"), _neutral("c"), _neutral("d"), _fav("e")]
    score = compute_confidence(factors)
    assert score.level == ConfidenceLevel.LOW
    assert score.favorable_count == 1

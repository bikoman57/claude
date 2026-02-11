from __future__ import annotations

from app.statistics.correlations import (
    CorrelationBreakdown,
    RiskIndicators,
)


def test_risk_indicators_flight_to_safety():
    ri = RiskIndicators(
        gold_price=200.0,
        gold_change_5d_pct=0.05,
        oil_price=70.0,
        oil_change_5d_pct=-0.02,
        dxy_price=104.0,
        dxy_change_5d_pct=0.01,
        flight_to_safety=True,
        risk_assessment="RISK_OFF",
        as_of="",
    )
    assert ri.flight_to_safety is True
    assert ri.risk_assessment == "RISK_OFF"


def test_risk_indicators_risk_on():
    ri = RiskIndicators(
        gold_price=180.0,
        gold_change_5d_pct=-0.03,
        oil_price=75.0,
        oil_change_5d_pct=0.02,
        dxy_price=102.0,
        dxy_change_5d_pct=-0.01,
        flight_to_safety=False,
        risk_assessment="RISK_ON",
        as_of="",
    )
    assert ri.risk_assessment == "RISK_ON"


def test_risk_indicators_neutral():
    ri = RiskIndicators(
        gold_price=190.0,
        gold_change_5d_pct=0.005,
        oil_price=72.0,
        oil_change_5d_pct=0.0,
        dxy_price=103.0,
        dxy_change_5d_pct=0.0,
        flight_to_safety=False,
        risk_assessment="NEUTRAL",
        as_of="",
    )
    assert ri.risk_assessment == "NEUTRAL"


def test_correlation_no_decoupling():
    cb = CorrelationBreakdown(
        spy_qqq_corr=0.95,
        spy_iwm_corr=0.85,
        decoupling_detected=False,
        decoupled_pairs=(),
    )
    assert cb.decoupling_detected is False


def test_correlation_decoupling():
    cb = CorrelationBreakdown(
        spy_qqq_corr=0.95,
        spy_iwm_corr=0.5,
        decoupling_detected=True,
        decoupled_pairs=("SPY-IWM",),
    )
    assert cb.decoupling_detected is True
    assert "SPY-IWM" in cb.decoupled_pairs

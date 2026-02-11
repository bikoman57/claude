from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FactorAssessment(StrEnum):
    """Assessment for a single confidence factor."""

    FAVORABLE = "FAVORABLE"
    UNFAVORABLE = "UNFAVORABLE"
    NEUTRAL = "NEUTRAL"


class ConfidenceLevel(StrEnum):
    """Overall confidence level."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class FactorResult:
    """Assessment of one confidence factor."""

    name: str
    assessment: FactorAssessment
    reason: str


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """Overall confidence score for a signal."""

    level: ConfidenceLevel
    favorable_count: int
    total_factors: int
    factors: tuple[FactorResult, ...]


def assess_drawdown_depth(
    drawdown_pct: float,
    threshold: float,
) -> FactorResult:
    """Assess drawdown depth relative to threshold."""
    abs_dd = abs(drawdown_pct)
    if abs_dd >= threshold * 1.5:
        return FactorResult(
            "drawdown_depth",
            FactorAssessment.FAVORABLE,
            f"Deep drawdown: {abs_dd:.1%}",
        )
    if abs_dd >= threshold:
        return FactorResult(
            "drawdown_depth",
            FactorAssessment.NEUTRAL,
            f"At threshold: {abs_dd:.1%}",
        )
    return FactorResult(
        "drawdown_depth",
        FactorAssessment.UNFAVORABLE,
        f"Shallow: {abs_dd:.1%}",
    )


def assess_vix_regime(vix_regime: str) -> FactorResult:
    """Assess VIX regime for mean-reversion."""
    if vix_regime in ("ELEVATED", "EXTREME"):
        return FactorResult(
            "vix_regime",
            FactorAssessment.FAVORABLE,
            f"VIX {vix_regime}: fear present",
        )
    if vix_regime == "NORMAL":
        return FactorResult(
            "vix_regime",
            FactorAssessment.NEUTRAL,
            "VIX normal range",
        )
    return FactorResult(
        "vix_regime",
        FactorAssessment.UNFAVORABLE,
        "VIX low: complacent market",
    )


def assess_fed_regime(trajectory: str) -> FactorResult:
    """Assess Fed trajectory for mean-reversion."""
    if trajectory == "CUTTING":
        return FactorResult(
            "fed_regime",
            FactorAssessment.FAVORABLE,
            "Fed cutting rates",
        )
    if trajectory == "HIKING":
        return FactorResult(
            "fed_regime",
            FactorAssessment.UNFAVORABLE,
            "Fed hiking rates",
        )
    return FactorResult(
        "fed_regime",
        FactorAssessment.NEUTRAL,
        f"Fed {trajectory.lower()}",
    )


def assess_yield_curve(curve_status: str) -> FactorResult:
    """Assess yield curve for mean-reversion."""
    if curve_status == "NORMAL":
        return FactorResult(
            "yield_curve",
            FactorAssessment.FAVORABLE,
            "Normal yield curve",
        )
    if curve_status == "INVERTED":
        return FactorResult(
            "yield_curve",
            FactorAssessment.UNFAVORABLE,
            "Inverted yield curve",
        )
    return FactorResult(
        "yield_curve",
        FactorAssessment.NEUTRAL,
        f"Yield curve {curve_status.lower()}",
    )


def assess_sec_sentiment(
    high_materiality_count: int,
) -> FactorResult:
    """Assess SEC filing sentiment (simplified v1)."""
    if high_materiality_count == 0:
        return FactorResult(
            "sec_sentiment",
            FactorAssessment.NEUTRAL,
            "No material filings",
        )
    if high_materiality_count > 3:
        return FactorResult(
            "sec_sentiment",
            FactorAssessment.UNFAVORABLE,
            f"{high_materiality_count} material filings",
        )
    return FactorResult(
        "sec_sentiment",
        FactorAssessment.NEUTRAL,
        f"{high_materiality_count} material filing(s)",
    )


def assess_geopolitical_risk(risk_level: str) -> FactorResult:
    """Assess geopolitical risk level for mean-reversion."""
    if risk_level == "LOW":
        return FactorResult(
            "geopolitical_risk",
            FactorAssessment.FAVORABLE,
            "Low geopolitical risk",
        )
    if risk_level == "HIGH":
        return FactorResult(
            "geopolitical_risk",
            FactorAssessment.UNFAVORABLE,
            "High geopolitical risk",
        )
    return FactorResult(
        "geopolitical_risk",
        FactorAssessment.NEUTRAL,
        f"Geopolitical risk {risk_level.lower()}",
    )


def assess_social_sentiment(sentiment: str) -> FactorResult:
    """Assess social media sentiment (contrarian: bearish = favorable)."""
    if sentiment == "BEARISH":
        return FactorResult(
            "social_sentiment",
            FactorAssessment.FAVORABLE,
            "Social sentiment bearish (contrarian)",
        )
    if sentiment == "BULLISH":
        return FactorResult(
            "social_sentiment",
            FactorAssessment.NEUTRAL,
            "Social sentiment bullish",
        )
    return FactorResult(
        "social_sentiment",
        FactorAssessment.NEUTRAL,
        "Social sentiment neutral",
    )


def assess_news_sentiment(sentiment: str) -> FactorResult:
    """Assess news sentiment (contrarian: bearish = favorable)."""
    if sentiment == "BEARISH":
        return FactorResult(
            "news_sentiment",
            FactorAssessment.FAVORABLE,
            "News sentiment bearish (contrarian)",
        )
    if sentiment == "BULLISH":
        return FactorResult(
            "news_sentiment",
            FactorAssessment.NEUTRAL,
            "News sentiment bullish",
        )
    return FactorResult(
        "news_sentiment",
        FactorAssessment.NEUTRAL,
        "News sentiment neutral",
    )


def assess_market_statistics(assessment: str) -> FactorResult:
    """Assess market statistics (contrarian: risk-off = favorable)."""
    if assessment == "RISK_OFF":
        return FactorResult(
            "market_statistics",
            FactorAssessment.FAVORABLE,
            "Market risk-off (contrarian opportunity)",
        )
    if assessment == "RISK_ON":
        return FactorResult(
            "market_statistics",
            FactorAssessment.NEUTRAL,
            "Market risk-on",
        )
    return FactorResult(
        "market_statistics",
        FactorAssessment.NEUTRAL,
        "Market statistics neutral",
    )


def compute_confidence(
    factors: list[FactorResult],
) -> ConfidenceScore:
    """Compute overall confidence from factor assessments.

    HIGH: 7+/9 favorable, MEDIUM: 4-6, LOW: 0-3.
    """
    favorable = sum(
        1
        for f in factors
        if f.assessment == FactorAssessment.FAVORABLE
    )
    total = len(factors)

    if favorable >= 7:
        level = ConfidenceLevel.HIGH
    elif favorable >= 4:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    return ConfidenceScore(
        level=level,
        favorable_count=favorable,
        total_factors=total,
        factors=tuple(factors),
    )

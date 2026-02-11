from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import yfinance as yf


@dataclass(frozen=True, slots=True)
class RiskIndicators:
    """Cross-asset risk indicators."""

    gold_price: float | None
    gold_change_5d_pct: float | None
    oil_price: float | None
    oil_change_5d_pct: float | None
    dxy_price: float | None
    dxy_change_5d_pct: float | None
    flight_to_safety: bool
    risk_assessment: str
    as_of: str


@dataclass(frozen=True, slots=True)
class CorrelationBreakdown:
    """Correlation analysis between tracked assets."""

    spy_qqq_corr: float | None
    spy_iwm_corr: float | None
    decoupling_detected: bool
    decoupled_pairs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StatisticsSummary:
    """Full statistics dashboard."""

    risk_indicators: RiskIndicators
    correlations: CorrelationBreakdown | None
    overall_assessment: str
    as_of: str


def _fetch_price_and_change(
    ticker: str,
) -> tuple[float | None, float | None]:
    """Fetch latest price and 5-day change for a ticker."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if len(hist) < 2:
            return None, None
        closes = hist["Close"]
        price = float(closes.iloc[-1])
        idx_5 = min(5, len(closes) - 1)
        change = (closes.iloc[-1] - closes.iloc[-idx_5]) / closes.iloc[-idx_5]
        return price, float(change)
    except Exception:
        return None, None


def fetch_risk_indicators() -> RiskIndicators:
    """Fetch cross-asset risk indicators."""
    gold_price, gold_change = _fetch_price_and_change("GLD")
    oil_price, oil_change = _fetch_price_and_change("USO")
    dxy_price, dxy_change = _fetch_price_and_change("DX-Y.NYB")

    # Flight to safety: gold up AND VIX rising
    flight = False
    if gold_change is not None and gold_change > 0.01:
        try:
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="5d")
            if len(vix_hist) >= 2:
                vix_change = (
                    float(vix_hist["Close"].iloc[-1]) - float(vix_hist["Close"].iloc[0])
                ) / float(vix_hist["Close"].iloc[0])
                if vix_change > 0.05:
                    flight = True
        except Exception:  # noqa: S110
            pass

    # Risk assessment
    if flight:
        assessment = "RISK_OFF"
    elif gold_change is not None and gold_change < -0.01:
        assessment = "RISK_ON"
    else:
        assessment = "NEUTRAL"

    return RiskIndicators(
        gold_price=gold_price,
        gold_change_5d_pct=gold_change,
        oil_price=oil_price,
        oil_change_5d_pct=oil_change,
        dxy_price=dxy_price,
        dxy_change_5d_pct=dxy_change,
        flight_to_safety=flight,
        risk_assessment=assessment,
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )


def calculate_correlations() -> CorrelationBreakdown | None:
    """Calculate rolling correlations between major indices."""
    try:
        spy = yf.Ticker("SPY").history(period="1mo")
        qqq = yf.Ticker("QQQ").history(period="1mo")
        iwm = yf.Ticker("IWM").history(period="1mo")

        if len(spy) < 10 or len(qqq) < 10 or len(iwm) < 10:
            return None

        # Calculate daily returns
        spy_ret = spy["Close"].pct_change().dropna()
        qqq_ret = qqq["Close"].pct_change().dropna()
        iwm_ret = iwm["Close"].pct_change().dropna()

        # Align lengths
        min_len = min(len(spy_ret), len(qqq_ret), len(iwm_ret))
        spy_r = spy_ret.iloc[-min_len:]
        qqq_r = qqq_ret.iloc[-min_len:]
        iwm_r = iwm_ret.iloc[-min_len:]

        spy_qqq = float(spy_r.corr(qqq_r))
        spy_iwm = float(spy_r.corr(iwm_r))

        decoupled: list[str] = []
        if spy_qqq < 0.7:
            decoupled.append("SPY-QQQ")
        if spy_iwm < 0.7:
            decoupled.append("SPY-IWM")

        return CorrelationBreakdown(
            spy_qqq_corr=spy_qqq,
            spy_iwm_corr=spy_iwm,
            decoupling_detected=len(decoupled) > 0,
            decoupled_pairs=tuple(decoupled),
        )
    except Exception:
        return None

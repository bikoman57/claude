"""HTML report generation for GitHub Pages — narrative dashboard layout."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime

from app.etf.confidence import (
    ConfidenceLevel,
    ConfidenceScore,
    FactorAssessment,
    FactorResult,
    assess_drawdown_depth,
    assess_fed_regime,
    assess_geopolitical_risk,
    assess_market_statistics,
    assess_news_sentiment,
    assess_sec_sentiment,
    assess_social_sentiment,
    assess_vix_regime,
    assess_yield_curve,
    compute_confidence,
)
from app.scheduler.runner import SchedulerRun

_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1200px; margin: 0 auto; padding: 24px;
  background: #0d1117; color: #c9d1d9; line-height: 1.6;
}
h1 { color: #e6edf3; font-size: 1.5em; font-weight: 600; }
h2 { color: #e6edf3; margin-bottom: 12px; font-size: 1.1em; font-weight: 600;
     text-transform: uppercase; letter-spacing: 0.05em; }
.header { display: flex; align-items: center; justify-content: space-between;
          border-bottom: 1px solid #30363d; padding-bottom: 16px;
          margin-bottom: 24px; flex-wrap: wrap; gap: 8px; }
.header-status { font-size: 0.9em; }

/* Executive summary */
.exec-summary { background: #161b22; border: 1px solid #30363d;
  border-left: 4px solid #58a6ff; border-radius: 8px; padding: 20px;
  margin-bottom: 24px; }
.exec-summary p { margin-bottom: 8px; }
.exec-summary .headline { font-size: 1.15em; color: #e6edf3; font-weight: 600; }
.exec-summary .detail { font-size: 0.95em; color: #8b949e; }

/* KPI strip */
.kpi-strip { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 12px; margin-bottom: 24px; }
.kpi-card { background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 16px; border-top: 3px solid #30363d;
  transition: transform 0.15s ease, box-shadow 0.15s ease; }
.kpi-card:hover { transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
.kpi-label { font-size: 0.75em; color: #8b949e; text-transform: uppercase;
  letter-spacing: 0.08em; margin-bottom: 4px; }
.kpi-value { font-size: 1.8em; font-weight: 700; color: #e6edf3;
  line-height: 1.2; }
.kpi-sub { font-size: 0.85em; color: #8b949e; margin-top: 4px; }
.kpi-bar-green { border-top-color: #238636; }
.kpi-bar-yellow { border-top-color: #9e6a03; }
.kpi-bar-red { border-top-color: #da3633; }
.kpi-bar-gray { border-top-color: #484f58; }

/* Gauge bar */
.gauge-track { height: 6px; background: #21262d; border-radius: 3px;
  margin-top: 8px; overflow: hidden; }
.gauge-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
.gauge-fill-green { background: #238636; }
.gauge-fill-yellow { background: #9e6a03; }
.gauge-fill-red { background: #da3633; }
.gauge-fill-gray { background: #484f58; }

/* Cards */
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 20px; margin-bottom: 24px;
  transition: transform 0.15s ease, box-shadow 0.15s ease; }
.card:hover { transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2); }

/* Grid layouts */
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

/* Badges */
.badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
  font-size: 0.8em; font-weight: 600; letter-spacing: 0.03em; }
.badge-green { background: #238636; color: #fff; }
.badge-yellow { background: #9e6a03; color: #fff; }
.badge-red { background: #da3633; color: #fff; }
.badge-gray { background: #30363d; color: #8b949e; }
.badge-blue { background: #1f6feb; color: #fff; }

/* Tables */
table { border-collapse: collapse; width: 100%; }
th { text-align: left; padding: 10px 12px; color: #8b949e; font-weight: 600;
  font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 2px solid #30363d; }
td { padding: 10px 12px; border-bottom: 1px solid #21262d; }
tbody tr:hover { background: #1c2128; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.pct-up { color: #3fb950; }
.pct-down { color: #f85149; }

/* Signal cards */
.signal-card { background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 16px; margin-bottom: 12px;
  border-left: 4px solid #30363d; }
.signal-card-signal { border-left-color: #3fb950; }
.signal-card-alert { border-left-color: #9e6a03; }
.signal-card-active { border-left-color: #1f6feb; }
.signal-card-watch { border-left-color: #484f58; }
.signal-card-target { border-left-color: #a371f7; }
.signal-header { display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px; }
.signal-ticker { font-size: 1.2em; font-weight: 700; color: #e6edf3; }
.signal-details { font-size: 0.9em; color: #8b949e; }

/* Confidence */
.confidence-bar { display: flex; gap: 3px; margin-top: 6px; }
.conf-dot { width: 12px; height: 12px; border-radius: 50%;
  background: #21262d; }
.conf-dot-favorable { background: #238636; }
.conf-dot-unfavorable { background: #da3633; }
.conf-dot-neutral { background: #484f58; }

/* Factor table in details */
.factor-table { width: 100%; margin-top: 8px; }
.factor-table td { padding: 4px 8px; font-size: 0.85em;
  border-bottom: 1px solid #21262d; }
.factor-table .factor-name { color: #8b949e; }

/* Sentiment bar */
.sentiment-bar { display: flex; height: 20px; border-radius: 4px;
  overflow: hidden; margin: 8px 0; }
.sentiment-fill-bullish { background: #238636; }
.sentiment-fill-bearish { background: #da3633; }
.sentiment-fill-neutral { background: #484f58; }
.sentiment-counts { display: flex; gap: 16px; font-size: 0.85em;
  color: #8b949e; margin-top: 4px; }
.sentiment-count-bullish { color: #3fb950; }
.sentiment-count-bearish { color: #f85149; }

/* Details/summary */
details { margin-top: 8px; }
summary { cursor: pointer; font-size: 0.85em; color: #58a6ff;
  padding: 4px 0; }
summary:hover { text-decoration: underline; }
details[open] summary { margin-bottom: 8px; }

/* Sector badges */
.sector-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.sector-badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 0.75em; background: #21262d; color: #8b949e; }

/* Indicators row */
.ind-row { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; }
.ind-item { display: flex; align-items: center; gap: 6px;
  font-size: 0.9em; }
.ind-label { color: #8b949e; }

/* Module pills */
.module-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.module-pill { display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 12px; border-radius: 16px; font-size: 0.8em;
  font-weight: 500; }
.module-pill-ok { background: #0d2818; color: #3fb950;
  border: 1px solid #238636; }
.module-pill-fail { background: #2d1214; color: #f85149;
  border: 1px solid #da3633; }
.pill-dur { color: #8b949e; font-size: 0.85em; }

/* Footer */
.footer { margin-top: 32px; padding-top: 16px;
  border-top: 1px solid #30363d; font-size: 0.85em; color: #8b949e;
  display: flex; justify-content: space-between; flex-wrap: wrap;
  gap: 8px; }
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.ok { color: #3fb950; }
.fail { color: #f85149; }

/* Index page */
.report-list { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px; margin-top: 16px; }
.report-card { background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 16px; text-align: center;
  transition: transform 0.15s ease, border-color 0.15s ease; }
.report-card:hover { transform: translateY(-2px);
  border-color: #58a6ff; }
.report-card a { font-size: 1.1em; font-weight: 600; }
.badge-latest { background: #1f6feb; color: #fff; font-size: 0.7em;
  padding: 2px 8px; border-radius: 8px; margin-left: 6px; }

@media (max-width: 768px) {
  .grid-2col { grid-template-columns: 1fr; }
  .header { flex-direction: column; align-items: flex-start; }
  .kpi-strip { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
  .kpi-value { font-size: 1.4em; }
}
"""

_BADGE_MAP: dict[str, str] = {
    "HIGH": "badge-red",
    "ELEVATED": "badge-red",
    "EXTREME": "badge-red",
    "BEARISH": "badge-red",
    "RISK_OFF": "badge-red",
    "BACKWARDATION": "badge-red",
    "HIKING": "badge-red",
    "INVERTED": "badge-red",
    "HAWKISH": "badge-yellow",
    "MEDIUM": "badge-yellow",
    "NORMAL": "badge-yellow",
    "NEUTRAL": "badge-gray",
    "FLAT": "badge-gray",
    "UNKNOWN": "badge-gray",
    "LOW": "badge-green",
    "CALM": "badge-green",
    "BULLISH": "badge-green",
    "RISK_ON": "badge-green",
    "CONTANGO": "badge-green",
    "CUTTING": "badge-green",
    "DOVISH": "badge-green",
    "FAVORABLE": "badge-green",
    "SIGNAL": "badge-green",
    "ACTIVE": "badge-blue",
    "ALERT": "badge-yellow",
    "WATCH": "badge-gray",
    "TARGET": "badge-green",
}

_KPI_BAR_MAP: dict[str, str] = {
    "badge-green": "kpi-bar-green",
    "badge-yellow": "kpi-bar-yellow",
    "badge-red": "kpi-bar-red",
    "badge-gray": "kpi-bar-gray",
    "badge-blue": "kpi-bar-gray",
}

_GAUGE_FILL_MAP: dict[str, str] = {
    "badge-green": "gauge-fill-green",
    "badge-yellow": "gauge-fill-yellow",
    "badge-red": "gauge-fill-red",
    "badge-gray": "gauge-fill-gray",
    "badge-blue": "gauge-fill-gray",
}


def _badge(level: str) -> str:
    """Return an HTML badge span for a risk/sentiment level."""
    cls = _BADGE_MAP.get(level.upper(), "badge-gray")
    return f'<span class="badge {cls}">{html.escape(level)}</span>'


def _kpi_bar_class(level: str) -> str:
    """Return the KPI card border-top color class for a level."""
    badge_cls = _BADGE_MAP.get(level.upper(), "badge-gray")
    return _KPI_BAR_MAP.get(badge_cls, "kpi-bar-gray")


def _gauge_fill_class(level: str) -> str:
    """Return gauge fill color class for a level."""
    badge_cls = _BADGE_MAP.get(level.upper(), "badge-gray")
    return _GAUGE_FILL_MAP.get(badge_cls, "gauge-fill-gray")


def _parse_output(
    output: str,
) -> dict[str, object] | list[object] | None:
    """Try to parse JSON from module output."""
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return None


def _fmt_pct(value: object, signed: bool = False) -> str:
    """Format a float as percentage string with optional sign."""
    if not isinstance(value, (int, float)):
        return "N/A"
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value:.1%}"


def _pct_class(value: object) -> str:
    """Return CSS class for a percentage value."""
    if not isinstance(value, (int, float)):
        return ""
    return "pct-up" if value >= 0 else "pct-down"


def _fmt_price(value: object) -> str:
    """Format a float as a price string."""
    if not isinstance(value, (int, float)):
        return "N/A"
    return f"${value:,.2f}"


def _gauge_bar(pct: float, level: str) -> str:
    """Render a horizontal gauge bar filled to pct (0-100)."""
    clamped = max(0.0, min(100.0, pct))
    fill_cls = _gauge_fill_class(level)
    return (
        '<div class="gauge-track">'
        f'<div class="gauge-fill {fill_cls}" style="width:{clamped:.0f}%">'
        "</div></div>"
    )


def _html_page(title: str, body: str) -> str:
    """Wrap body content in a full HTML5 page with inline CSS."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{_CSS}</style>\n"
        f"</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


# --- Confidence computation from module outputs ---


def _compute_signal_confidence(
    outputs: dict[str, str],
    signal: dict[str, object],
) -> ConfidenceScore:
    """Compute confidence for a single ETF signal using all available data."""
    factors: list[FactorResult] = []

    # 1. Drawdown depth
    dd = signal.get("underlying_drawdown_pct", 0)
    threshold = signal.get("profit_target_pct", 0.10)
    if isinstance(dd, (int, float)) and isinstance(threshold, (int, float)):
        factors.append(assess_drawdown_depth(dd, max(threshold, 0.05)))

    # 2. VIX regime
    macro = _parse_output(outputs.get("macro.dashboard", ""))
    vix_regime = "UNKNOWN"
    if isinstance(macro, dict):
        vix_regime = str(macro.get("vix_regime", "UNKNOWN"))
    factors.append(assess_vix_regime(vix_regime))

    # 3. Fed regime
    rates = _parse_output(outputs.get("macro.rates", ""))
    trajectory = "UNKNOWN"
    if isinstance(rates, dict):
        trajectory = str(rates.get("trajectory", "UNKNOWN"))
    factors.append(assess_fed_regime(trajectory))

    # 4. Yield curve
    yields = _parse_output(outputs.get("macro.yields", ""))
    curve = "UNKNOWN"
    if isinstance(yields, dict):
        curve = str(yields.get("curve_status", "UNKNOWN"))
    factors.append(assess_yield_curve(curve))

    # 5. SEC filings
    factors.append(assess_sec_sentiment(0))

    # 6. Geopolitical
    geo = _parse_output(outputs.get("geopolitical.summary", ""))
    geo_risk = "UNKNOWN"
    if isinstance(geo, dict):
        geo_risk = str(geo.get("risk_level", "UNKNOWN"))
    factors.append(assess_geopolitical_risk(geo_risk))

    # 7. Social sentiment
    social = _parse_output(outputs.get("social.summary", ""))
    social_tone = "NEUTRAL"
    if isinstance(social, dict):
        officials = social.get("officials", {})
        if isinstance(officials, dict):
            social_tone = str(officials.get("fed_tone", "NEUTRAL"))
    factors.append(assess_social_sentiment(social_tone))

    # 8. News sentiment
    news = _parse_output(outputs.get("news.summary", ""))
    news_sent = "NEUTRAL"
    if isinstance(news, dict):
        news_sent = str(news.get("sentiment", "NEUTRAL"))
    factors.append(assess_news_sentiment(news_sent))

    # 9. Market statistics
    stats = _parse_output(outputs.get("statistics.dashboard", ""))
    mkt_assess = "NEUTRAL"
    if isinstance(stats, dict):
        risk_ind = stats.get("risk_indicators", {})
        if isinstance(risk_ind, dict):
            mkt_assess = str(risk_ind.get("risk_assessment", "NEUTRAL"))
    factors.append(assess_market_statistics(mkt_assess))

    return compute_confidence(factors)


def _render_confidence_dots(score: ConfidenceScore) -> str:
    """Render confidence as colored dots."""
    dots: list[str] = []
    for f in score.factors:
        if f.assessment == FactorAssessment.FAVORABLE:
            cls = "conf-dot-favorable"
        elif f.assessment == FactorAssessment.UNFAVORABLE:
            cls = "conf-dot-unfavorable"
        else:
            cls = "conf-dot-neutral"
        title = f"{html.escape(f.name)}: {html.escape(f.reason)}"
        dots.append(
            f'<span class="conf-dot {cls}" title="{title}"></span>',
        )
    return f'<div class="confidence-bar">{"".join(dots)}</div>'


def _render_factor_table(score: ConfidenceScore) -> str:
    """Render a detailed factor breakdown table."""
    rows: list[str] = []
    for f in score.factors:
        name = html.escape(f.name.replace("_", " ").title())
        reason = html.escape(f.reason)
        badge = _badge(str(f.assessment))
        rows.append(
            f'<tr><td class="factor-name">{name}</td>'
            f"<td>{badge}</td>"
            f"<td>{reason}</td></tr>",
        )
    return (
        '<table class="factor-table"><tbody>'
        + "\n".join(rows)
        + "</tbody></table>"
    )


# --- KPI card helpers ---


def _kpi_card(
    label: str,
    value: str,
    level: str,
    sub: str = "",
    gauge_pct: float | None = None,
) -> str:
    """Render a single KPI metric card with optional gauge bar."""
    bar = _kpi_bar_class(level)
    parts = [
        f'<div class="kpi-card {bar}">',
        f'<div class="kpi-label">{html.escape(label)}</div>',
        f'<div class="kpi-value">{value}</div>',
    ]
    if sub:
        parts.append(f'<div class="kpi-sub">{sub}</div>')
    if gauge_pct is not None:
        parts.append(_gauge_bar(gauge_pct, level))
    parts.append("</div>")
    return "\n".join(parts)


def _section_kpi_strip(outputs: dict[str, str]) -> str:
    """Render the top KPI metric strip with gauge bars."""
    cards: list[str] = []

    # VIX — scale 0-50
    macro = _parse_output(outputs.get("macro.dashboard", ""))
    if isinstance(macro, dict):
        vix_val = macro.get("vix", None)
        vix_regime = str(macro.get("vix_regime", "N/A"))
        vix_display = (
            f"{vix_val:.1f}" if isinstance(vix_val, (int, float)) else "N/A"
        )
        gauge = (
            (float(vix_val) / 50.0) * 100.0
            if isinstance(vix_val, (int, float))
            else None
        )
        cards.append(_kpi_card(
            "VIX", vix_display, vix_regime, _badge(vix_regime),
            gauge_pct=gauge,
        ))

    # Fed trajectory — from macro.rates
    rates = _parse_output(outputs.get("macro.rates", ""))
    if isinstance(macro, dict):
        fed = "N/A"
        rate_sub = ""
        if isinstance(rates, dict):
            fed = str(rates.get("trajectory", "N/A"))
            current_rate = rates.get("current_rate", None)
            if isinstance(current_rate, (int, float)):
                rate_sub = f"{current_rate:.2f}%"
        elif isinstance(macro, dict):
            fed_rate = macro.get("fed_funds_rate", None)
            if isinstance(fed_rate, (int, float)):
                rate_sub = f"{fed_rate:.2f}%"
        cards.append(_kpi_card("Fed", _badge(fed), fed, rate_sub))

    # Yield curve — spread scale -2 to +2
    yields = _parse_output(outputs.get("macro.yields", ""))
    if isinstance(yields, dict):
        curve = str(yields.get("curve_status", "N/A"))
        spread = yields.get("spread_3m_10y", None)
        spread_sub = (
            f"Spread: {spread:+.2f}%"
            if isinstance(spread, (int, float))
            else ""
        )
        gauge = (
            ((float(spread) + 2.0) / 4.0) * 100.0
            if isinstance(spread, (int, float))
            else None
        )
        cards.append(_kpi_card(
            "Yield Curve", _badge(curve), curve, spread_sub,
            gauge_pct=gauge,
        ))

    # Geopolitical
    geo = _parse_output(outputs.get("geopolitical.summary", ""))
    if isinstance(geo, dict):
        risk = str(geo.get("risk_level", "N/A"))
        events = geo.get("total_events", 0)
        cards.append(_kpi_card(
            "Geopolitical",
            _badge(risk),
            risk,
            f"{html.escape(str(events))} events",
        ))

    # News sentiment — with article counts
    news = _parse_output(outputs.get("news.summary", ""))
    if isinstance(news, dict):
        sentiment = str(news.get("sentiment", "N/A"))
        articles = news.get("total_articles", 0)
        cards.append(_kpi_card(
            "News",
            _badge(sentiment),
            sentiment,
            f"{html.escape(str(articles))} articles",
        ))

    if not cards:
        return ""
    return (
        '<div class="kpi-strip">\n'
        + "\n".join(cards)
        + "\n</div>\n"
    )


# --- Executive summary ---


def _section_executive_summary(
    outputs: dict[str, str],
    signals: list[dict[str, object]],
) -> str:
    """Generate a narrative executive summary."""
    # Count signals by state
    signal_count = sum(
        1 for s in signals
        if isinstance(s.get("state"), str) and s["state"] == "SIGNAL"
    )
    alert_count = sum(
        1 for s in signals
        if isinstance(s.get("state"), str) and s["state"] == "ALERT"
    )
    active_count = sum(
        1 for s in signals
        if isinstance(s.get("state"), str) and s["state"] == "ACTIVE"
    )

    # Compute a representative confidence for the best signal
    best_confidence: ConfidenceScore | None = None
    signal_etfs = [
        s for s in signals
        if isinstance(s.get("state"), str) and s["state"] == "SIGNAL"
    ]
    if signal_etfs:
        best_confidence = _compute_signal_confidence(outputs, signal_etfs[0])

    # Gather factors for narrative
    favorable_factors: list[str] = []
    unfavorable_factors: list[str] = []
    if best_confidence:
        for f in best_confidence.factors:
            if f.assessment == FactorAssessment.FAVORABLE:
                favorable_factors.append(f.reason)
            elif f.assessment == FactorAssessment.UNFAVORABLE:
                unfavorable_factors.append(f.reason)

    # Build narrative
    lines: list[str] = []

    # Headline
    if signal_count > 0 and best_confidence:
        if best_confidence.level == ConfidenceLevel.HIGH:
            stance = "favor"
        elif best_confidence.level == ConfidenceLevel.MEDIUM:
            stance = "are mixed for"
        else:
            stance = "oppose"
        conf_str = (
            f"{best_confidence.favorable_count}/{best_confidence.total_factors}"
        )
        headline = (
            f"Market conditions {stance} mean-reversion entries. "
            f"{signal_count} ETF(s) at actionable SIGNAL level "
            f"with {best_confidence.level} confidence ({conf_str})."
        )
    elif alert_count > 0:
        headline = (
            f"No ETFs at SIGNAL level. {alert_count} ETF(s) approaching "
            f"entry thresholds at ALERT level. Monitoring for deeper drawdowns."
        )
    elif active_count > 0:
        headline = (
            f"{active_count} active position(s) being tracked. "
            "No new entry signals today."
        )
    else:
        headline = (
            "No actionable signals today. "
            f"{len(signals)} ETF(s) being monitored across the universe."
        )

    lines.append(f'<p class="headline">{html.escape(headline)}</p>')

    # Key support / risk factors
    if favorable_factors:
        support = html.escape(favorable_factors[0])
        lines.append(f'<p class="detail">Key support: {support}</p>')
    if unfavorable_factors:
        risk = html.escape(unfavorable_factors[0])
        lines.append(f'<p class="detail">Key risk: {risk}</p>')

    if not lines:
        return ""
    return (
        '<div class="exec-summary">\n'
        + "\n".join(lines)
        + "\n</div>\n"
    )


# --- ETF signal cards ---


def _section_etf_signals(
    outputs: dict[str, str],
    signals: list[dict[str, object]],
) -> str:
    """Render ETF signals as individual cards with confidence drill-down."""
    if not signals:
        return ""
    cards: list[str] = []
    for sig in signals[:10]:
        if not isinstance(sig, dict):
            continue
        ticker = html.escape(str(sig.get("leveraged_ticker", "?")))
        underlying = html.escape(str(sig.get("underlying_ticker", "")))
        state = str(sig.get("state", "?"))
        state_lower = state.lower()
        dd = sig.get("underlying_drawdown_pct", 0)
        dd_str = _fmt_pct(dd)
        ath = sig.get("underlying_ath", None)
        current = sig.get("underlying_current", None)
        pl = sig.get("current_pl_pct", None)
        entry_price = sig.get("leveraged_entry_price", None)
        target_pct = sig.get("profit_target_pct", 0.10)

        # Compute confidence
        confidence = _compute_signal_confidence(outputs, sig)

        # Card wrapper
        card_cls = f"signal-card signal-card-{state_lower}"
        parts: list[str] = [f'<div class="{card_cls}">']

        # Header row: ticker, state, confidence
        parts.append('<div class="signal-header">')
        parts.append(
            f'<span><span class="signal-ticker">{ticker}</span> '
            f"({underlying}) &mdash; {_badge(state)}</span>",
        )
        conf_badge = _badge(str(confidence.level))
        parts.append(
            f"<span>Confidence: {conf_badge} "
            f"({confidence.favorable_count}/{confidence.total_factors})"
            "</span>",
        )
        parts.append("</div>")

        # Details row
        detail_parts = [f"Drawdown: {html.escape(dd_str)}"]
        if isinstance(ath, (int, float)):
            detail_parts.append(f"ATH: {_fmt_price(ath)}")
        if isinstance(current, (int, float)):
            detail_parts.append(f"Current: {_fmt_price(current)}")
        if isinstance(entry_price, (int, float)):
            detail_parts.append(f"Entry: {_fmt_price(entry_price)}")
        if isinstance(target_pct, (int, float)):
            detail_parts.append(f"Target: {_fmt_pct(target_pct)}")
        if isinstance(pl, (int, float)):
            pl_cls = _pct_class(pl)
            detail_parts.append(
                f'P&L: <span class="{pl_cls}">'
                f"{_fmt_pct(pl, signed=True)}</span>",
            )

        parts.append(
            '<div class="signal-details">'
            + " &bull; ".join(detail_parts)
            + "</div>",
        )

        # Confidence dots
        parts.append(_render_confidence_dots(confidence))

        # Drill-down: factor breakdown
        parts.append("<details>")
        parts.append("<summary>View 9-factor analysis</summary>")
        parts.append(_render_factor_table(confidence))
        parts.append("</details>")

        parts.append("</div>")
        cards.append("\n".join(parts))

    if not cards:
        return ""
    return (
        "<h2>Entry Signals &amp; Active Positions</h2>\n"
        + "\n".join(cards)
        + "\n"
    )


# --- Sentiment section ---


def _section_sentiment(outputs: dict[str, str]) -> str:
    """Render sentiment analysis with visual bars and drill-down."""
    parts: list[str] = []

    news = _parse_output(outputs.get("news.summary", ""))
    if isinstance(news, dict):
        sentiment = str(news.get("sentiment", "N/A"))
        bullish = news.get("bullish_count", 0)
        bearish = news.get("bearish_count", 0)
        neutral = news.get("neutral_count", 0)

        bullish = int(bullish) if isinstance(bullish, (int, float)) else 0
        bearish = int(bearish) if isinstance(bearish, (int, float)) else 0
        neutral = int(neutral) if isinstance(neutral, (int, float)) else 0

        total = bullish + bearish + neutral
        if total > 0:
            b_pct = (bullish / total) * 100
            r_pct = (bearish / total) * 100
            n_pct = (neutral / total) * 100
        else:
            b_pct = r_pct = 0.0
            n_pct = 100.0

        parts.append(f"<p>News Sentiment: {_badge(sentiment)}</p>")
        parts.append(
            '<div class="sentiment-bar">'
            f'<div class="sentiment-fill-bullish" style="width:{b_pct:.1f}%"></div>'
            f'<div class="sentiment-fill-bearish" style="width:{r_pct:.1f}%"></div>'
            f'<div class="sentiment-fill-neutral" style="width:{n_pct:.1f}%"></div>'
            "</div>",
        )
        parts.append(
            '<div class="sentiment-counts">'
            f'<span class="sentiment-count-bullish">{bullish} bullish</span>'
            f'<span class="sentiment-count-bearish">{bearish} bearish</span>'
            f"<span>{neutral} neutral</span>"
            "</div>",
        )

        # Headlines drill-down
        headlines = news.get("top_headlines", [])
        if isinstance(headlines, list) and headlines:
            parts.append("<details>")
            parts.append("<summary>Top headlines</summary>")
            parts.append("<ul>")
            for h in headlines[:8]:
                if isinstance(h, dict):
                    title = html.escape(str(h.get("title", "")))
                    h_sent = str(h.get("sentiment", ""))
                    h_badge = _badge(h_sent) if h_sent else ""
                    parts.append(f"<li>{title} {h_badge}</li>")
            parts.append("</ul>")
            parts.append("</details>")

        # Sector mentions
        sectors = news.get("sector_mentions", {})
        if isinstance(sectors, dict) and sectors:
            sorted_sectors = sorted(
                sectors.items(),
                key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                reverse=True,
            )
            parts.append('<div class="sector-badges">')
            for name, count in sorted_sectors[:8]:
                parts.append(
                    f'<span class="sector-badge">'
                    f"{html.escape(str(name))} ({count})"
                    "</span>",
                )
            parts.append("</div>")

    # Officials tone from social
    social = _parse_output(outputs.get("social.summary", ""))
    if isinstance(social, dict):
        officials = social.get("officials", {})
        if isinstance(officials, dict):
            tone = str(officials.get("fed_tone", "N/A"))
            policy = str(officials.get("policy_direction", ""))
            stmts = officials.get("total_statements", 0)
            parts.append(
                f'<p style="margin-top:12px">Officials Tone: {_badge(tone)}',
            )
            if policy and policy != "N/A":
                parts.append(f" &nbsp; Policy: {_badge(policy)}")
            if isinstance(stmts, (int, float)) and stmts > 0:
                parts.append(
                    f' <span style="color:#8b949e">({int(stmts)} statements)</span>',
                )
            parts.append("</p>")

    if not parts:
        return ""
    return (
        "<h2>Sentiment Analysis</h2>\n"
        '<div class="card">\n'
        + "\n".join(parts)
        + "\n</div>\n"
    )


# --- Market conditions section ---


def _section_market_conditions(outputs: dict[str, str]) -> str:
    """Render market conditions: risk indicators, commodities, correlations."""
    parts: list[str] = []

    stats = _parse_output(outputs.get("statistics.dashboard", ""))
    if isinstance(stats, dict):
        risk = stats.get("risk_indicators", {})
        if isinstance(risk, dict):
            assessment = str(risk.get("risk_assessment", "N/A"))
            parts.append(
                f"<p>Risk Assessment: {_badge(assessment)}</p>",
            )

            indicators: list[str] = []
            for asset, label in [
                ("gold", "Gold"),
                ("oil", "Oil"),
                ("dxy", "DXY"),
            ]:
                price = risk.get(f"{asset}_price")
                chg = risk.get(f"{asset}_change_5d_pct")
                if isinstance(price, (int, float)):
                    chg_str = ""
                    if isinstance(chg, (int, float)):
                        cls = _pct_class(chg)
                        chg_str = (
                            f' <span class="{cls}">'
                            f"{_fmt_pct(chg, signed=True)}</span>"
                        )
                    indicators.append(
                        f'<span class="ind-item">'
                        f'<span class="ind-label">{label}:</span> '
                        f"{_fmt_price(price)}{chg_str}</span>",
                    )
            if indicators:
                parts.append(
                    '<div class="ind-row">'
                    + "".join(indicators)
                    + "</div>",
                )

        # Correlations
        corr = stats.get("correlations", {})
        if isinstance(corr, dict):
            decoupled = corr.get("decoupled_pairs", [])
            if isinstance(decoupled, list) and decoupled:
                pairs = ", ".join(
                    html.escape(str(p)) for p in decoupled[:4]
                )
                parts.append(
                    f'<p style="margin-top:8px">'
                    f'<span class="badge badge-yellow">DECOUPLING</span> '
                    f"{pairs}</p>",
                )

    if not parts:
        return ""
    return (
        "<h2>Market Conditions</h2>\n"
        '<div class="card">\n'
        + "\n".join(parts)
        + "\n</div>\n"
    )


# --- Strategy section ---


def _section_strategy(outputs: dict[str, str]) -> str:
    """Render strategy backtest results with drill-down."""
    if "strategy.proposals" not in outputs:
        return ""
    data = _parse_output(outputs["strategy.proposals"])
    if not isinstance(data, list) or not data:
        return ""
    rows: list[str] = []
    for p in data[:8]:
        if not isinstance(p, dict):
            continue
        ticker = html.escape(str(p.get("leveraged_ticker", "?")))
        reason = html.escape(str(p.get("improvement_reason", "")))
        sharpe = p.get("backtest_sharpe", None)
        sharpe_str = (
            f"{sharpe:.2f}" if isinstance(sharpe, (int, float)) else "N/A"
        )
        wr = p.get("backtest_win_rate", None)
        wr_str = _fmt_pct(wr) if isinstance(wr, (int, float)) else "N/A"
        ret = p.get("backtest_total_return", None)
        ret_str = (
            _fmt_pct(ret, signed=True)
            if isinstance(ret, (int, float))
            else "N/A"
        )
        ret_cls = _pct_class(ret)

        rows.append(
            f"<tr><td><strong>{ticker}</strong></td>"
            f"<td>{reason}</td>"
            f'<td class="num">{html.escape(sharpe_str)}</td>'
            f'<td class="num">{html.escape(wr_str)}</td>'
            f'<td class="num {ret_cls}">{html.escape(ret_str)}</td></tr>',
        )
    if not rows:
        return ""
    return (
        "<h2>Strategy Backtest Results</h2>\n"
        '<div class="card">\n<table>\n'
        "<thead><tr>"
        "<th>ETF</th><th>Proposal</th>"
        "<th>Sharpe</th><th>Win Rate</th><th>Return</th>"
        "</tr></thead>\n<tbody>\n"
        + "\n".join(rows)
        + "\n</tbody></table>\n</div>\n"
    )


# --- Module status ---


def _section_module_status(run: SchedulerRun) -> str:
    """Render module execution status as compact pills."""
    pills: list[str] = []
    for r in run.results:
        cls = "module-pill-ok" if r.success else "module-pill-fail"
        icon = "&#10003;" if r.success else "&#10007;"
        name = html.escape(r.name)
        dur = f"{r.duration_seconds:.1f}s"
        pills.append(
            f'<span class="module-pill {cls}">'
            f"{icon} {name} "
            f'<span class="pill-dur">{dur}</span></span>',
        )
    return (
        "<h2>Module Status</h2>\n"
        '<div class="card">\n'
        '<div class="module-grid">\n'
        + "\n".join(pills)
        + "\n</div>\n</div>\n"
    )


# --- Page builders ---


def build_html_report(
    run: SchedulerRun,
    *,
    date: str = "",
) -> str:
    """Build a complete narrative HTML dashboard from a scheduler run."""
    report_date = date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    outputs: dict[str, str] = {}
    for result in run.results:
        if result.success and result.output.strip():
            outputs[result.name] = result.output.strip()

    # Parse signals for signal cards + exec summary
    signals_data = _parse_output(outputs.get("etf.signals", ""))
    signals: list[dict[str, object]] = []
    if isinstance(signals_data, list):
        signals = [s for s in signals_data if isinstance(s, dict)]

    # Build sections
    exec_summary = _section_executive_summary(outputs, signals)
    kpi = _section_kpi_strip(outputs)
    signal_cards = _section_etf_signals(outputs, signals)
    sentiment = _section_sentiment(outputs)
    conditions = _section_market_conditions(outputs)
    strategy = _section_strategy(outputs)
    modules = _section_module_status(run)

    # Header
    header = (
        '<div class="header">\n'
        "<h1>Daily Swing Trading Dashboard &mdash; "
        f"{html.escape(report_date)}</h1>\n"
        '<div class="header-status">'
        f'<span class="ok">{run.succeeded}</span>/{run.total_modules} OK'
        f' &nbsp; <span class="fail">{run.failed}</span> failed'
        "</div>\n</div>\n"
    )

    # Mid-section: two-column grid for sentiment + market conditions
    mid = ""
    if sentiment or conditions:
        if sentiment and conditions:
            mid = (
                '<div class="grid-2col">\n'
                f"<div>{sentiment}</div>\n"
                f"<div>{conditions}</div>\n"
                "</div>\n"
            )
        else:
            mid = sentiment + conditions

    footer = (
        '<div class="footer">\n'
        f"<span>Generated {html.escape(report_date)} &mdash; "
        "not financial advice.</span>\n"
        '<span><a href="../index.html">All Reports</a></span>\n'
        "</div>\n"
    )

    body_parts = [
        header, exec_summary, kpi, signal_cards,
        mid, strategy, modules, footer,
    ]
    return _html_page(
        title=f"Dashboard {report_date}",
        body="\n".join(p for p in body_parts if p),
    )


def build_index_html(report_dates: list[str]) -> str:
    """Build the index.html landing page with card-based report list."""
    cards: list[str] = []
    for i, d in enumerate(report_dates):
        escaped = html.escape(d)
        latest = (
            '<span class="badge-latest">LATEST</span>'
            if i == 0 and report_dates
            else ""
        )
        cards.append(
            f'<div class="report-card">'
            f'<a href="reports/{escaped}.html">'
            f"{escaped}</a>{latest}</div>",
        )

    list_html = (
        '<div class="report-list">\n'
        + "\n".join(cards)
        + "\n</div>"
        if cards
        else ""
    )

    body = (
        '<div class="header">\n'
        "<h1>Leveraged ETF Swing Trading Reports</h1>\n"
        f'<div class="header-status">'
        f"{len(report_dates)} report(s)</div>\n"
        "</div>\n"
        f"{list_html}\n"
        '<div class="footer">\n'
        '<span>Powered by <a href="https://github.com/bikoman57/claude">'
        "fin-agents</a></span>\n</div>"
    )
    return _html_page(title="Trading Reports", body=body)

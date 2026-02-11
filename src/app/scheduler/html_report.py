"""HTML report generation for GitHub Pages — dashboard layout."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime

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
}

_KPI_BAR_MAP: dict[str, str] = {
    "badge-green": "kpi-bar-green",
    "badge-yellow": "kpi-bar-yellow",
    "badge-red": "kpi-bar-red",
    "badge-gray": "kpi-bar-gray",
}


def _badge(level: str) -> str:
    """Return an HTML badge span for a risk/sentiment level."""
    cls = _BADGE_MAP.get(level.upper(), "badge-gray")
    return f'<span class="badge {cls}">{html.escape(level)}</span>'


def _kpi_bar_class(level: str) -> str:
    """Return the KPI card border-top color class for a level."""
    badge_cls = _BADGE_MAP.get(level.upper(), "badge-gray")
    return _KPI_BAR_MAP.get(badge_cls, "kpi-bar-gray")


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


# --- KPI card helpers ---


def _kpi_card(
    label: str,
    value: str,
    level: str,
    sub: str = "",
) -> str:
    """Render a single KPI metric card."""
    bar = _kpi_bar_class(level)
    parts = [
        f'<div class="kpi-card {bar}">',
        f'<div class="kpi-label">{html.escape(label)}</div>',
        f'<div class="kpi-value">{value}</div>',
    ]
    if sub:
        parts.append(f'<div class="kpi-sub">{sub}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def _section_kpi_strip(outputs: dict[str, str]) -> str:
    """Render the top KPI metric strip from multiple module outputs."""
    cards: list[str] = []

    # VIX
    macro = _parse_output(outputs.get("macro.dashboard", ""))
    if isinstance(macro, dict):
        vix_val = macro.get("vix", None)
        vix_regime = str(macro.get("vix_regime", "N/A"))
        vix_display = (
            f"{vix_val:.1f}" if isinstance(vix_val, (int, float)) else "N/A"
        )
        cards.append(_kpi_card(
            "VIX", vix_display, vix_regime, _badge(vix_regime),
        ))

    # Fed trajectory
    if isinstance(macro, dict):
        fed = str(macro.get("fed_trajectory", "N/A"))
        rate = macro.get("fed_funds_rate", None)
        rate_sub = (
            f"{rate:.2f}%" if isinstance(rate, (int, float)) else ""
        )
        cards.append(_kpi_card("Fed", _badge(fed), fed, rate_sub))

    # Yield curve
    yields = _parse_output(outputs.get("macro.yields", ""))
    if isinstance(yields, dict):
        curve = str(yields.get("curve_status", "N/A"))
        spread = yields.get("spread_3m_10y", None)
        spread_sub = (
            f"Spread: {spread:+.2f}%"
            if isinstance(spread, (int, float))
            else ""
        )
        cards.append(_kpi_card("Yield Curve", _badge(curve), curve, spread_sub))

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

    # News sentiment
    news = _parse_output(outputs.get("news.summary", ""))
    if isinstance(news, dict):
        sentiment = str(news.get("overall_sentiment", "N/A"))
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


# --- Section builders ---


def _section_etf_signals(outputs: dict[str, str]) -> str:
    """Render the ETF entry signals table with full details."""
    if "etf.scan" not in outputs:
        return ""
    data = _parse_output(outputs["etf.scan"])
    if not isinstance(data, list) or not data:
        return ""
    rows: list[str] = []
    for sig in data[:8]:
        if not isinstance(sig, dict):
            continue
        ticker = html.escape(str(sig.get("leveraged_ticker", "?")))
        underlying = html.escape(str(sig.get("underlying_ticker", "")))
        state = str(sig.get("state", "?"))
        dd = sig.get("underlying_drawdown_pct", 0)
        dd_str = _fmt_pct(dd)
        dd_cls = _pct_class(dd if isinstance(dd, (int, float)) else 0)
        ath = sig.get("underlying_ath", None)
        current = sig.get("underlying_current", None)
        pl = sig.get("current_pl_pct", None)
        pl_cell = ""
        if isinstance(pl, (int, float)):
            pl_cell = (
                f'<span class="{_pct_class(pl)}">{_fmt_pct(pl, signed=True)}'
                f"</span>"
            )

        rows.append(
            f"<tr><td><strong>{ticker}</strong></td>"
            f"<td>{underlying}</td>"
            f"<td>{_badge(state)}</td>"
            f'<td class="num {dd_cls}">{html.escape(dd_str)}</td>'
            f'<td class="num">{_fmt_price(ath)}</td>'
            f'<td class="num">{_fmt_price(current)}</td>'
            f'<td class="num">{pl_cell}</td></tr>',
        )
    if not rows:
        return ""
    return (
        "<h2>Entry Signals</h2>\n"
        '<div class="card">\n<table>\n'
        "<thead><tr>"
        "<th>ETF</th><th>Underlying</th><th>State</th>"
        "<th>Drawdown</th><th>ATH</th><th>Current</th><th>P&amp;L</th>"
        "</tr></thead>\n<tbody>\n"
        + "\n".join(rows)
        + "\n</tbody></table>\n</div>\n"
    )


def _section_strategy(outputs: dict[str, str]) -> str:
    """Render strategy proposals with backtest metrics."""
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
        ret_str = _fmt_pct(ret, signed=True) if isinstance(ret, (int, float)) else "N/A"
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
        "<h2>Strategy Proposals</h2>\n"
        '<div class="card">\n<table>\n'
        "<thead><tr>"
        "<th>ETF</th><th>Proposal</th>"
        "<th>Sharpe</th><th>Win Rate</th><th>Return</th>"
        "</tr></thead>\n<tbody>\n"
        + "\n".join(rows)
        + "\n</tbody></table>\n</div>\n"
    )


def _section_market_indicators(outputs: dict[str, str]) -> str:
    """Render market indicators: risk, commodities, correlations, officials."""
    parts: list[str] = []

    # Statistics risk
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

    # Social / officials tone
    social = _parse_output(outputs.get("social.summary", ""))
    if isinstance(social, dict):
        officials = social.get("officials", {})
        if isinstance(officials, dict):
            tone = str(officials.get("overall_tone", "N/A"))
            policy = str(officials.get("policy_direction", ""))
            tone_line = f"<p>Officials Tone: {_badge(tone)}"
            if policy and policy != "N/A":
                tone_line += f" &nbsp; Policy: {_badge(policy)}"
            tone_line += "</p>"
            parts.append(tone_line)

    if not parts:
        return ""
    return (
        "<h2>Market Indicators</h2>\n"
        '<div class="card">\n'
        + "\n".join(parts)
        + "\n</div>\n"
    )


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
    """Build a complete HTML dashboard page from a scheduler run."""
    report_date = date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    outputs: dict[str, str] = {}
    for result in run.results:
        if result.success and result.output.strip():
            outputs[result.name] = result.output.strip()

    kpi = _section_kpi_strip(outputs)
    signals = _section_etf_signals(outputs)
    strategy = _section_strategy(outputs)
    indicators = _section_market_indicators(outputs)
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

    # Mid-section: two-column grid if both sides have content
    mid = ""
    if strategy or indicators:
        if strategy and indicators:
            mid = (
                '<div class="grid-2col">\n'
                f"<div>{strategy}</div>\n"
                f"<div>{indicators}</div>\n"
                "</div>\n"
            )
        else:
            mid = strategy + indicators

    footer = (
        '<div class="footer">\n'
        f"<span>Generated {html.escape(report_date)} &mdash; "
        "not financial advice.</span>\n"
        '<span><a href="../index.html">All Reports</a></span>\n'
        "</div>\n"
    )

    body_parts = [header, kpi, signals, mid, modules, footer]
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

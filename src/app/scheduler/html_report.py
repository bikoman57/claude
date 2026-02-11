"""HTML report generation for GitHub Pages."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime

from app.scheduler.runner import SchedulerRun

_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 900px; margin: 0 auto; padding: 20px;
  background: #0d1117; color: #c9d1d9; line-height: 1.5;
}
h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 12px;
     margin-bottom: 16px; font-size: 1.6em; }
h2 { color: #79c0ff; margin-top: 24px; margin-bottom: 8px; font-size: 1.2em; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 6px;
        padding: 16px; margin: 12px 0; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
         font-size: 0.85em; font-weight: 600; }
.badge-green { background: #238636; color: #fff; }
.badge-yellow { background: #9e6a03; color: #fff; }
.badge-red { background: #da3633; color: #fff; }
.badge-gray { background: #30363d; color: #8b949e; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #30363d; }
th { color: #8b949e; font-weight: 600; }
.footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #30363d;
          font-size: 0.85em; color: #8b949e; }
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.ok { color: #3fb950; }
.fail { color: #f85149; }
.summary { font-size: 1.05em; margin-bottom: 16px; }
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


def _badge(level: str) -> str:
    """Return an HTML badge span for a risk/sentiment level."""
    cls = _BADGE_MAP.get(level.upper(), "badge-gray")
    return f'<span class="badge {cls}">{html.escape(level)}</span>'


def _parse_output(
    output: str,
) -> dict[str, object] | list[object] | None:
    """Try to parse JSON from module output."""
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return None


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


def _section_market_overview(outputs: dict[str, str]) -> str:
    if "macro.dashboard" not in outputs:
        return ""
    data = _parse_output(outputs["macro.dashboard"])
    if not isinstance(data, dict):
        return ""
    vix = str(data.get("vix_regime", "N/A"))
    fed = str(data.get("fed_trajectory", "N/A"))
    return (
        "<h2>Market Overview</h2>\n"
        '<div class="card">\n'
        f"<p>VIX Regime: {_badge(vix)} &nbsp; "
        f"Fed Trajectory: {_badge(fed)}</p>\n"
        "</div>\n"
    )


def _section_geopolitical(outputs: dict[str, str]) -> str:
    if "geopolitical.summary" not in outputs:
        return ""
    data = _parse_output(outputs["geopolitical.summary"])
    if not isinstance(data, dict):
        return ""
    risk = str(data.get("risk_level", "N/A"))
    events = data.get("total_events", 0)
    return (
        "<h2>Geopolitical Risk</h2>\n"
        '<div class="card">\n'
        f"<p>Risk Level: {_badge(risk)} &nbsp; "
        f"Events: {html.escape(str(events))}</p>\n"
        "</div>\n"
    )


def _section_social(outputs: dict[str, str]) -> str:
    if "social.summary" not in outputs:
        return ""
    data = _parse_output(outputs["social.summary"])
    if not isinstance(data, dict):
        return ""
    officials = data.get("officials", {})
    tone = "N/A"
    if isinstance(officials, dict):
        tone = str(officials.get("overall_tone", "N/A"))
    return (
        "<h2>Social &amp; Officials</h2>\n"
        '<div class="card">\n'
        f"<p>Officials Tone: {_badge(tone)}</p>\n"
        "</div>\n"
    )


def _section_news(outputs: dict[str, str]) -> str:
    if "news.summary" not in outputs:
        return ""
    data = _parse_output(outputs["news.summary"])
    if not isinstance(data, dict):
        return ""
    sentiment = str(data.get("overall_sentiment", "N/A"))
    count = data.get("total_articles", 0)
    return (
        "<h2>News Sentiment</h2>\n"
        '<div class="card">\n'
        f"<p>Sentiment: {_badge(sentiment)} &nbsp; "
        f"Articles: {html.escape(str(count))}</p>\n"
        "</div>\n"
    )


def _section_statistics(outputs: dict[str, str]) -> str:
    if "statistics.dashboard" not in outputs:
        return ""
    data = _parse_output(outputs["statistics.dashboard"])
    if not isinstance(data, dict):
        return ""
    risk = data.get("risk_indicators", {})
    assessment = "N/A"
    if isinstance(risk, dict):
        assessment = str(risk.get("risk_assessment", "N/A"))
    return (
        "<h2>Market Statistics</h2>\n"
        '<div class="card">\n'
        f"<p>Risk Assessment: {_badge(assessment)}</p>\n"
        "</div>\n"
    )


def _section_etf_signals(outputs: dict[str, str]) -> str:
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
        state = str(sig.get("state", "?"))
        dd = sig.get("underlying_drawdown_pct", 0)
        dd_str = f"{dd:.1%}" if isinstance(dd, float) else str(dd)
        rows.append(
            f"<tr><td>{ticker}</td>"
            f"<td>{_badge(state)}</td>"
            f"<td>{html.escape(dd_str)}</td></tr>",
        )
    if not rows:
        return ""
    return (
        "<h2>Entry Signals</h2>\n"
        '<div class="card">\n<table>\n'
        "<tr><th>ETF</th><th>State</th><th>Drawdown</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>\n</div>\n"
    )


def _section_strategy(outputs: dict[str, str]) -> str:
    if "strategy.proposals" not in outputs:
        return ""
    data = _parse_output(outputs["strategy.proposals"])
    if not isinstance(data, list) or not data:
        return ""
    rows: list[str] = []
    for p in data[:5]:
        if not isinstance(p, dict):
            continue
        ticker = html.escape(str(p.get("leveraged_ticker", "?")))
        reason = html.escape(str(p.get("improvement_reason", "")))
        rows.append(f"<tr><td>{ticker}</td><td>{reason}</td></tr>")
    if not rows:
        return ""
    return (
        "<h2>Strategy Insights</h2>\n"
        '<div class="card">\n<table>\n'
        "<tr><th>ETF</th><th>Proposal</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>\n</div>\n"
    )


def _section_module_status(run: SchedulerRun) -> str:
    rows: list[str] = []
    for r in run.results:
        icon = '<span class="ok">&#10003;</span>' if r.success else (
            '<span class="fail">&#10007;</span>'
        )
        name = html.escape(r.name)
        dur = f"{r.duration_seconds:.1f}s"
        rows.append(
            f"<tr><td>{icon}</td><td>{name}</td><td>{dur}</td></tr>",
        )
    return (
        "<h2>Module Status</h2>\n"
        '<div class="card">\n<table>\n'
        "<tr><th></th><th>Module</th><th>Duration</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>\n</div>\n"
    )


def build_html_report(
    run: SchedulerRun,
    *,
    date: str = "",
) -> str:
    """Build a complete HTML report page from a scheduler run."""
    report_date = date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    outputs: dict[str, str] = {}
    for result in run.results:
        if result.success and result.output.strip():
            outputs[result.name] = result.output.strip()

    sections = [
        _section_market_overview(outputs),
        _section_geopolitical(outputs),
        _section_social(outputs),
        _section_news(outputs),
        _section_statistics(outputs),
        _section_etf_signals(outputs),
        _section_strategy(outputs),
        _section_module_status(run),
    ]

    body_parts = [
        "<h1>Daily Swing Trading Report &mdash; "
        f"{html.escape(report_date)}</h1>",
        '<p class="summary">'
        f'Modules: <span class="ok">{run.succeeded}</span>'
        f"/{run.total_modules} OK"
        f' | Failed: <span class="fail">{run.failed}</span></p>',
        *[s for s in sections if s],
        '<p class="footer">'
        f"Generated {html.escape(report_date)} | "
        '<a href="../index.html">All Reports</a> | '
        "This is not financial advice.</p>",
    ]

    return _html_page(
        title=f"Report {report_date}",
        body="\n".join(body_parts),
    )


def build_index_html(report_dates: list[str]) -> str:
    """Build the index.html landing page listing all reports."""
    rows: list[str] = []
    for d in report_dates:
        escaped = html.escape(d)
        rows.append(
            f'<li><a href="reports/{escaped}.html">'
            f"{escaped}</a></li>",
        )

    list_html = "<ul>\n" + "\n".join(rows) + "\n</ul>" if rows else ""

    body = (
        "<h1>Leveraged ETF Swing Trading Reports</h1>\n"
        f"<p>{len(report_dates)} report(s) available.</p>\n"
        f"{list_html}\n"
        '<p class="footer">Powered by '
        '<a href="https://github.com/bikoman57/claude">'
        "fin-agents</a></p>"
    )
    return _html_page(title="Trading Reports", body=body)

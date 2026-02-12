"""HTML report generation for GitHub Pages — narrative dashboard layout."""

from __future__ import annotations

import html
import json
from datetime import datetime
from zoneinfo import ZoneInfo

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

_ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

_CSS = """\
/* === Editorial / Financial Times Design === */
:root {
  --bg-primary: #f8f6f1;
  --bg-secondary: #ffffff;
  --bg-tertiary: #f0ece3;
  --bg-dark: #16192b;
  --border-primary: #d4c9b8;
  --border-light: #e8dfcf;
  --border-hover: #990f3d;
  --text-primary: #1a1a1a;
  --text-secondary: #4a4a4a;
  --text-muted: #7a7a7a;
  --accent: #990f3d;
  --accent-light: #fce4ec;
  --success: #0a7c42;
  --success-bg: #e8f5e9;
  --warning: #b86e00;
  --warning-bg: #fff8e1;
  --danger: #c62828;
  --danger-bg: #ffebee;
  --info: #1565c0;
  --info-bg: #e3f2fd;
  --purple: #6a1b9a;
  --purple-bg: #f3e5f5;
  --neutral: #78909c;
  --font-serif: 'Playfair Display', Georgia, serif;
  --font-sans: 'Source Sans 3', -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', 'Consolas', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font-sans);
  width: 100%; margin: 0 auto; padding: 0 clamp(16px, 3vw, 48px);
  background: var(--bg-primary); color: var(--text-secondary); line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
h1 { font-family: var(--font-serif); color: var(--text-primary);
  font-size: 26px; font-weight: 700; letter-spacing: -0.01em; }
h2 { font-family: var(--font-serif); color: var(--text-primary);
  margin-bottom: 16px; font-size: 20px; font-weight: 700;
  padding-bottom: 8px; border-bottom: 2px solid var(--accent);
  display: inline-block; }

/* Material icon sizing */
.material-symbols-outlined {
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  vertical-align: middle;
}

/* Skip navigation */
.skip-nav { position: absolute; left: -9999px; top: auto;
  width: 1px; height: 1px; overflow: hidden;
  z-index: 1000; padding: 8px 16px;
  background: var(--accent); color: #fff;
  font-weight: 600; text-decoration: none; }
.skip-nav:focus { position: fixed; left: 50%; transform: translateX(-50%);
  top: 0; width: auto; height: auto; overflow: visible; }

/* Utility classes */
.mt-8 { margin-top: 8px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.text-muted { color: var(--text-muted); }

/* Navigation menu */
.nav-menu { position: sticky; top: 0; z-index: 100;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-light);
  padding: 0 clamp(16px, 3vw, 48px);
  margin: 0 calc(-1 * clamp(16px, 3vw, 48px));
  display: flex; gap: 0; overflow-x: auto;
  -webkit-overflow-scrolling: touch; }
.nav-menu a { font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text-muted); white-space: nowrap;
  padding: 14px 16px; border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s; }
.nav-menu a:hover, .nav-menu a:focus { color: var(--accent);
  border-bottom-color: var(--accent); text-decoration: none; }

/* Masthead */
.masthead { background: var(--bg-dark); color: #fff;
  padding: 20px clamp(16px, 3vw, 48px);
  margin: 0 calc(-1 * clamp(16px, 3vw, 48px)) 0;
  display: flex; justify-content: space-between; align-items: center; }
.masthead h1 { color: #fff; }
.masthead-meta { font-size: 13px; opacity: 0.7; text-align: right; }
.masthead-rule { height: 4px; background: var(--accent);
  margin: 0 calc(-1 * clamp(16px, 3vw, 48px)) 0; }

/* Header / datebar */
.header { display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid var(--border-primary); padding: 12px 0;
  margin-bottom: 28px; flex-wrap: wrap; gap: 8px;
  font-size: 13px; color: var(--text-muted); }
.header-status { font-size: 0.9em; font-family: var(--font-serif);
  font-style: italic; color: var(--text-secondary); }

/* Executive summary / lede */
.exec-summary { margin-bottom: 32px; padding-bottom: 28px;
  border-bottom: 2px solid var(--text-primary); }
.exec-summary p { margin-bottom: 8px; }
.exec-summary .headline { font-family: var(--font-serif);
  font-size: 28px; font-weight: 700; line-height: 1.3;
  color: var(--text-primary); letter-spacing: -0.01em; }
.exec-summary .detail { font-size: 16px; color: var(--text-secondary);
  line-height: 1.6; }

/* KPI strip — spacious cards with prominent icons */
.kpi-strip { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px; margin-bottom: 32px; }
.kpi-card { padding: 20px 24px;
  background: var(--bg-secondary); border: 1px solid var(--border-light);
  border-radius: 8px; position: relative; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kpi-card::before { content: ''; position: absolute; left: 0; top: 0;
  bottom: 0; width: 4px; }
.kpi-bar-green::before { background: var(--success); }
.kpi-bar-yellow::before { background: var(--warning); }
.kpi-bar-red::before { background: var(--danger); }
.kpi-bar-gray::before { background: var(--neutral); }
.kpi-icon { display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px; }
.kpi-icon .material-symbols-outlined { font-size: 28px; color: var(--accent);
  font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 28; }
.kpi-label { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.1em; }
.kpi-value { font-family: var(--font-serif); font-size: 32px;
  font-weight: 700; color: var(--text-primary); line-height: 1.1;
  margin-top: 4px; }
.kpi-sub { font-size: 13px; color: var(--text-muted); margin-top: 8px; }

/* Gauge bar */
.gauge-track { height: 4px; background: var(--bg-tertiary);
  border-radius: 2px; margin-top: 10px; overflow: hidden; }
.gauge-fill { height: 100%; border-radius: 2px; }
.gauge-fill-green { background: var(--success); }
.gauge-fill-yellow { background: var(--warning); }
.gauge-fill-red { background: var(--danger); }
.gauge-fill-gray { background: var(--neutral); }

/* Cards */
.card { background: var(--bg-secondary); border: 1px solid var(--border-light);
  padding: 24px; margin-bottom: 24px; border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04); }

/* Grid layouts */
.grid-2col { display: grid; grid-template-columns: 1.4fr 1fr; gap: 32px; }

/* Badges */
.badge { display: inline-block; padding: 3px 10px; border-radius: 3px;
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.06em; text-transform: uppercase; }
.badge-green { background: var(--success-bg); color: var(--success); }
.badge-yellow { background: var(--warning-bg); color: var(--warning); }
.badge-red { background: var(--danger-bg); color: var(--danger); }
.badge-gray { background: var(--bg-tertiary); color: var(--text-muted); }
.badge-blue { background: var(--info-bg); color: var(--info); }

/* Tables */
table { border-collapse: collapse; width: 100%; }
th { font-family: var(--font-mono); text-align: left; padding: 10px 14px;
  color: var(--text-muted); font-weight: 600; font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.08em;
  border-bottom: 2px solid var(--text-primary); }
td { padding: 12px 14px; border-bottom: 1px solid var(--border-light); }
tbody tr:hover { background: var(--bg-tertiary); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.pct-up { color: var(--success); }
.pct-down { color: var(--danger); }

/* Signal cards — grid layout */
.signal-grid { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px; margin-bottom: 16px; }
.signal-card { background: var(--bg-secondary); border: 1px solid var(--border-light);
  padding: 16px 20px; border-left: 4px solid var(--border-light);
  border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.signal-card-signal { border-left-color: var(--success);
  border-left-width: 5px; background: var(--success-bg); }
.signal-card-signal .signal-ticker { font-size: 1.35em; }
.signal-card-alert { border-left-color: var(--warning); }
.signal-card-active { border-left-color: var(--info); }
.signal-card-watch { border-left-color: var(--neutral); }
.signal-card-target { border-left-color: var(--purple); }
.signal-header { display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px; }
.signal-ticker { font-family: var(--font-mono); font-size: 15px;
  font-weight: 700; color: var(--text-primary); }
.signal-details { font-size: 0.9em; color: var(--text-muted);
  font-variant-numeric: tabular-nums; }

/* Confidence dots */
.confidence-bar { display: flex; gap: 3px; margin-top: 8px; }
.conf-dot { width: 12px; height: 12px; border-radius: 50%;
  background: var(--bg-tertiary); display: flex; align-items: center;
  justify-content: center; font-size: 8px; font-weight: 700; line-height: 1; }
.conf-dot-favorable { background: var(--success); color: #fff; }
.conf-dot-unfavorable { background: var(--danger); color: #fff; }
.conf-dot-neutral { background: var(--border-primary); color: var(--text-muted); }

/* Factor table */
.factor-table { width: 100%; margin-top: 8px; }
.factor-table td { padding: 4px 8px; font-size: 0.85em;
  border-bottom: 1px solid var(--border-light); }
.factor-table .factor-name { color: var(--text-muted); }

/* Sentiment bar */
.sentiment-bar { display: flex; height: 12px;
  overflow: hidden; margin: 10px 0; border-radius: 6px; }
.sentiment-fill-bullish { background: var(--success); }
.sentiment-fill-bearish { background: var(--danger); }
.sentiment-fill-neutral { background: var(--border-primary); }
.sentiment-counts { display: flex; gap: 16px; font-size: 12px;
  font-family: var(--font-mono); color: var(--text-muted); margin-top: 4px; }
.sentiment-count-bullish { color: var(--success); font-weight: 600; }
.sentiment-count-bearish { color: var(--danger); font-weight: 600; }

/* Details/summary */
details { margin-top: 8px; }
summary { cursor: pointer; font-family: var(--font-mono); font-size: 11px;
  color: var(--accent); padding: 6px 0; min-height: 44px;
  display: flex; align-items: center; gap: 8px; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary::before { content: "\\25B6"; font-size: 0.65em;
  transition: transform 0.15s ease; display: inline-block; }
details[open] summary::before { transform: rotate(90deg); }
summary:hover { text-decoration: underline; }
details[open] summary { margin-bottom: 8px; }

/* Sector badges */
.sector-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.sector-badge { font-family: var(--font-mono); font-size: 10px;
  padding: 3px 8px; background: var(--bg-tertiary); color: var(--text-muted);
  border: 1px solid var(--border-light); border-radius: 3px; }

/* Index tiles — major market indices */
.index-tiles { display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 12px; margin-bottom: 16px; }
.index-tile { text-align: center; padding: 16px;
  background: var(--bg-secondary); border: 1px solid var(--border-light);
  border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.index-name { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.08em; font-weight: 600; }
.index-price { font-family: var(--font-serif); font-size: 22px;
  font-weight: 700; color: var(--text-primary); margin-top: 4px; }
.index-chg { font-family: var(--font-mono); font-size: 13px;
  font-weight: 600; margin-top: 2px; }

/* Commodity tiles */
.commodity-tiles { display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 12px; margin-top: 16px; }
.commodity-tile { text-align: center; padding: 14px;
  background: var(--bg-tertiary); border-radius: 4px; }
.commodity-name { font-family: var(--font-mono); font-size: 10px;
  color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.08em; }
.commodity-price { font-family: var(--font-serif); font-size: 20px;
  font-weight: 700; color: var(--text-primary); margin-top: 2px; }
.commodity-chg { font-family: var(--font-mono); font-size: 12px;
  font-weight: 600; }

/* Global rates table */
.rates-grid { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px; margin-top: 12px; }
.rate-tile { text-align: center; padding: 10px;
  background: var(--bg-tertiary); border-radius: 4px; }
.rate-bank { font-family: var(--font-mono); font-size: 10px;
  color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.08em; }
.rate-value { font-family: var(--font-serif); font-size: 18px;
  font-weight: 700; color: var(--text-primary); margin-top: 2px; }

/* Geopolitical events */
.geo-events { margin-top: 12px; }
.geo-event { padding: 10px 0;
  border-bottom: 1px solid var(--border-light); }
.geo-event:last-child { border-bottom: none; }
.geo-title { font-size: 14px; color: var(--text-secondary); }
.geo-title a { font-weight: 500; }
.geo-meta { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); margin-top: 4px;
  display: flex; gap: 12px; flex-wrap: wrap; }

/* Standfirst highlight */
.highlight { background: linear-gradient(transparent 60%, var(--accent-light) 60%);
  padding: 0 2px; }

/* Lede kicker */
.kicker { font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em;
  margin-bottom: 8px; }

/* Trade count warning */
.trade-count { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); }
.trade-count-warn { color: var(--warning); }

/* Strategy detail row */
.strategy-detail { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); margin-top: 4px; }
.strategy-detail span { margin-right: 12px; }
.strategy-entry-exit { display: flex; gap: 16px; flex-wrap: wrap;
  padding: 8px 14px; background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-light); font-size: 12px;
  font-family: var(--font-mono); color: var(--text-secondary); }
.strategy-entry-exit .label { color: var(--text-muted); font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px; }

/* Headline list */
.headline-list { list-style: none; margin-top: 12px; padding: 0; }
.headline-list li { padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
  font-size: 14px; color: var(--text-secondary); line-height: 1.5; }
.headline-list li:last-child { border-bottom: none; }
.headline-list a { font-weight: 500; }
.hl-marker { font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  padding: 2px 6px; border-radius: 2px; margin-right: 8px;
  text-transform: uppercase; display: inline-block; }
.hl-bull { background: var(--success-bg); color: var(--success); }
.hl-bear { background: var(--danger-bg); color: var(--danger); }
.hl-neu { background: var(--bg-tertiary); color: var(--text-muted); }
.hl-source { font-family: var(--font-mono); font-size: 10px;
  color: var(--text-muted); margin-left: 6px; }

/* Module pills */
.module-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.module-pill { display: inline-flex; align-items: center; gap: 4px;
  font-family: var(--font-mono); padding: 3px 10px; font-size: 10px;
  font-weight: 500; border-radius: 3px; }
.module-pill-ok { background: var(--success-bg); color: var(--success); }
.module-pill-fail { background: var(--danger-bg); color: var(--danger); }
.pill-dur { color: var(--text-muted); font-size: 0.85em; }

/* Section icons */
.section-icon { display: inline-flex; align-items: center; gap: 8px; }
.section-icon .material-symbols-outlined { font-size: 24px;
  color: var(--accent); vertical-align: middle; }

/* Indicators row */
.ind-row { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; }
.ind-item { display: flex; align-items: center; gap: 8px;
  font-size: 0.9em; font-variant-numeric: tabular-nums; }
.ind-label { color: var(--text-muted); font-family: var(--font-mono);
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; }

/* Footer */
.footer { margin-top: 40px; padding: 20px 0;
  border-top: 3px solid var(--text-primary); font-size: 12px;
  color: var(--text-muted); display: flex; justify-content: space-between;
  flex-wrap: wrap; gap: 8px; }
a { color: var(--accent); text-decoration: none; font-weight: 600; }
a:hover { text-decoration: underline; }
.ok { color: var(--success); }
.fail { color: var(--danger); }

/* Index page */
.report-list { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px; margin-top: 16px; }
.report-card { background: var(--bg-secondary); border: 1px solid var(--border-light);
  padding: 16px; text-align: center; position: relative;
  transition: border-color 0.15s ease; border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.report-card:hover { border-color: var(--accent); }
.report-card a { font-family: var(--font-serif); font-size: 1.1em;
  font-weight: 600; }
.report-card a::after { content: ''; position: absolute;
  inset: 0; z-index: 1; }
.badge-latest { background: var(--accent); color: #fff; font-size: 0.7em;
  font-family: var(--font-mono); padding: 2px 8px; margin-left: 8px;
  text-transform: uppercase; letter-spacing: 0.06em; border-radius: 3px; }

/* Focus-visible */
a:focus-visible, summary:focus-visible, .report-card:focus-within {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* Tablet */
@media (max-width: 900px) {
  .grid-2col { grid-template-columns: 1fr; }
  .signal-grid { grid-template-columns: 1fr; }
  .kpi-strip { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
  table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .index-tiles { grid-template-columns: repeat(3, 1fr); }
}

/* Mobile */
@media (max-width: 600px) {
  .commodity-tiles { grid-template-columns: repeat(2, 1fr); }
  .index-tiles { grid-template-columns: 1fr; }
  .header { flex-direction: column; align-items: flex-start; }
  .kpi-strip { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .kpi-value { font-size: 1.4em; }
  .exec-summary .headline { font-size: 22px; }
  .signal-grid { grid-template-columns: 1fr; }
  .rates-grid { grid-template-columns: repeat(2, 1fr); }
  .nav-menu a { padding: 12px 12px; font-size: 10px; }
  .strategy-entry-exit { flex-direction: column; gap: 4px; }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}

/* Print */
@media print {
  body { background: #fff; color: #000; max-width: 100%;
    font-size: 11pt; }
  .masthead { background: #000; }
  .masthead-rule { background: #000; }
  .card, .signal-card, .kpi-card, .exec-summary, .report-card {
    background: #fff; border-color: #ccc; box-shadow: none;
    break-inside: avoid; }
  .skip-nav, .nav-menu { display: none; }
  details[open] > summary { display: none; }
  details > *:not(summary) { display: block !important; }
  details:not([open]) { display: block; }
  details:not([open]) > *:not(summary) { display: block !important; }
  details:not([open]) > summary { display: none; }
  .badge { border: 1px solid currentColor; }
  a { color: #000; text-decoration: underline; }
  .footer { page-break-before: auto; }
  .report-card:hover { transform: none; }
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
    "CONTRACTIONARY": "badge-gray",
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

# Confidence uses separate color mapping: HIGH=good, LOW=bad for trades
_CONFIDENCE_BADGE_MAP: dict[str, str] = {
    "HIGH": "badge-green",
    "MEDIUM": "badge-yellow",
    "LOW": "badge-red",
}

# Signal state display priority: actionable states first
_STATE_PRIORITY: dict[str, int] = {
    "SIGNAL": 0,
    "ACTIVE": 1,
    "ALERT": 2,
    "TARGET": 3,
    "WATCH": 4,
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

# Google Material Symbols icon names
_MATERIAL_ICONS: dict[str, str] = {
    "signal": "radar",
    "news": "newspaper",
    "globe": "public",
    "strategy": "analytics",
    "conditions": "monitoring",
    "vix": "trending_up",
    "rate": "account_balance",
    "yield": "show_chart",
    "rates": "currency_exchange",
}


def _material_icon(name: str, size: int = 24) -> str:
    """Return a Google Material Symbols icon span."""
    icon = _MATERIAL_ICONS.get(name, "")
    if not icon:
        return ""
    return (
        f'<span class="material-symbols-outlined"'
        f' style="font-size:{size}px">{icon}</span>'
    )


def _icon(name: str) -> str:
    """Return a KPI card icon."""
    icon = _MATERIAL_ICONS.get(name, "")
    if not icon:
        return ""
    return (
        f'<div class="kpi-icon">'
        f'<span class="material-symbols-outlined">{icon}</span>'
        f"</div>"
    )


def _section_icon(name: str) -> str:
    """Return an icon for section headers."""
    icon = _MATERIAL_ICONS.get(name, "")
    if not icon:
        return ""
    return (
        f'<span class="section-icon">'
        f'<span class="material-symbols-outlined">{icon}</span>'
        f"</span> "
    )


def _badge(level: str) -> str:
    """Return an HTML badge span for a risk/sentiment level."""
    cls = _BADGE_MAP.get(level.upper(), "badge-gray")
    return f'<span class="badge {cls}">{html.escape(level)}</span>'


def _confidence_badge(level: str) -> str:
    """Return a badge for confidence level (HIGH=green, LOW=red)."""
    cls = _CONFIDENCE_BADGE_MAP.get(level.upper(), "badge-gray")
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


def _gauge_bar(pct: float, level: str, label: str = "") -> str:
    """Render a horizontal gauge bar filled to pct (0-100)."""
    clamped = max(0.0, min(100.0, pct))
    fill_cls = _gauge_fill_class(level)
    aria = (
        f' role="progressbar" aria-valuenow="{clamped:.0f}"'
        ' aria-valuemin="0" aria-valuemax="100"'
    )
    if label:
        aria += f' aria-label="{html.escape(label)}"'
    return (
        f'<div class="gauge-track"{aria}>'
        f'<div class="gauge-fill {fill_cls}" style="width:{clamped:.0f}%">'
        "</div></div>"
    )


def _html_page(title: str, body: str, *, description: str = "") -> str:
    """Wrap body content in a full HTML5 page with inline CSS."""
    desc_tag = ""
    if description:
        desc_tag = f'<meta name="description" content="{html.escape(description)}">\n'
    fonts = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        "<link"
        ' href="https://fonts.googleapis.com/css2?'
        "family=IBM+Plex+Mono:wght@400;500;600&amp;"
        "family=Playfair+Display:wght@400;500;600;700;800&amp;"
        'family=Source+Sans+3:wght@300;400;500;600;700&amp;display=swap"'
        ' rel="stylesheet">\n'
        "<link"
        ' href="https://fonts.googleapis.com/css2?'
        "family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
        '" rel="stylesheet">\n'
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en" dir="ltr">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="theme-color" content="#16192b">\n'
        f"{desc_tag}"
        f"<title>{html.escape(title)}</title>\n"
        f"{fonts}"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        '<a href="#main-content" class="skip-nav">Skip to main content</a>\n'
        f"{body}\n</body>\n</html>\n"
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


_DOT_SYMBOLS: dict[FactorAssessment, str] = {
    FactorAssessment.FAVORABLE: "+",
    FactorAssessment.UNFAVORABLE: "-",
    FactorAssessment.NEUTRAL: "~",
}


def _render_confidence_dots(score: ConfidenceScore) -> str:
    """Render confidence as colored dots with symbols for accessibility."""
    dots: list[str] = []
    for f in score.factors:
        if f.assessment == FactorAssessment.FAVORABLE:
            cls = "conf-dot-favorable"
        elif f.assessment == FactorAssessment.UNFAVORABLE:
            cls = "conf-dot-unfavorable"
        else:
            cls = "conf-dot-neutral"
        title = f"{html.escape(f.name)}: {html.escape(f.reason)}"
        symbol = _DOT_SYMBOLS.get(f.assessment, "~")
        aria_label = f"{html.escape(f.name)}: {html.escape(str(f.assessment.name))}"
        dots.append(
            f'<span class="conf-dot {cls}" title="{title}" '
            f'role="img" aria-label="{aria_label}">{symbol}</span>',
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
    return '<table class="factor-table"><tbody>' + "\n".join(rows) + "</tbody></table>"


# --- KPI card helpers ---


def _kpi_card(
    label: str,
    value: str,
    level: str,
    sub: str = "",
    gauge_pct: float | None = None,
    icon_name: str = "",
) -> str:
    """Render a single KPI metric card with optional gauge bar and icon."""
    bar = _kpi_bar_class(level)
    icon_html = _icon(icon_name) if icon_name else ""
    parts = [
        f'<div class="kpi-card {bar}">',
        f'{icon_html}<div class="kpi-label">{html.escape(label)}</div>',
        f'<div class="kpi-value">{value}</div>',
    ]
    if sub:
        parts.append(f'<div class="kpi-sub">{sub}</div>')
    if gauge_pct is not None:
        parts.append(_gauge_bar(gauge_pct, level, label=f"{label} gauge"))
    parts.append("</div>")
    return "\n".join(parts)


def _section_kpi_strip(outputs: dict[str, str]) -> str:
    """Render the top KPI metric strip with gauge bars."""
    cards: list[str] = []

    # VIX -- scale 0-50
    macro = _parse_output(outputs.get("macro.dashboard", ""))
    if isinstance(macro, dict):
        vix_val = macro.get("vix", None)
        vix_regime = str(macro.get("vix_regime", "N/A"))
        vix_display = f"{vix_val:.1f}" if isinstance(vix_val, (int, float)) else "N/A"
        gauge = (
            (float(vix_val) / 50.0) * 100.0
            if isinstance(vix_val, (int, float))
            else None
        )
        cards.append(
            _kpi_card(
                "VIX",
                vix_display,
                vix_regime,
                _badge(vix_regime),
                gauge_pct=gauge,
                icon_name="vix",
            )
        )

    # Fed trajectory -- from macro.rates
    rates = _parse_output(outputs.get("macro.rates", ""))
    if isinstance(macro, dict):
        fed = "N/A"
        rate_display = "--"
        rate_sub_parts: list[str] = []
        if isinstance(rates, dict):
            fed = str(rates.get("trajectory", "N/A"))
            current_rate = rates.get("current_rate", None)
            if isinstance(current_rate, (int, float)):
                rate_display = f"{current_rate:.2f}%"
            rate_sub_parts.append(_badge(fed))
        elif isinstance(macro, dict):
            fed_rate = macro.get("fed_funds_rate", None)
            if isinstance(fed_rate, (int, float)):
                rate_display = f"{fed_rate:.2f}%"
        cards.append(
            _kpi_card(
                "Fed",
                rate_display,
                fed,
                " ".join(rate_sub_parts),
                icon_name="rate",
            ),
        )

    # Yield curve -- spread scale -2 to +2
    yields = _parse_output(outputs.get("macro.yields", ""))
    if isinstance(yields, dict):
        curve = str(yields.get("curve_status", "N/A"))
        spread = yields.get("spread_3m_10y", None)
        spread_display = f"{spread:+.2f}%" if isinstance(spread, (int, float)) else "--"
        spread_sub = _badge(curve)
        gauge = (
            ((float(spread) + 2.0) / 4.0) * 100.0
            if isinstance(spread, (int, float))
            else None
        )
        cards.append(
            _kpi_card(
                "Yield Curve",
                spread_display,
                curve,
                spread_sub,
                gauge_pct=gauge,
                icon_name="yield",
            )
        )

    # Geopolitical
    geo = _parse_output(outputs.get("geopolitical.summary", ""))
    if isinstance(geo, dict):
        risk = str(geo.get("risk_level", "N/A"))
        events = geo.get("total_events", 0)
        events_display = html.escape(str(events))
        cards.append(
            _kpi_card(
                "Geopolitical",
                events_display,
                risk,
                f"{_badge(risk)} {html.escape(str(events))} events",
                icon_name="globe",
            )
        )

    # News sentiment
    news = _parse_output(outputs.get("news.summary", ""))
    if isinstance(news, dict):
        sentiment = str(news.get("sentiment", "N/A"))
        articles = news.get("total_articles", 0)
        articles_display = html.escape(str(articles))
        cards.append(
            _kpi_card(
                "News",
                articles_display,
                sentiment,
                f"{_badge(sentiment)} {html.escape(str(articles))} articles",
                icon_name="news",
            )
        )

    if not cards:
        return ""
    return '<div class="kpi-strip">\n' + "\n".join(cards) + "\n</div>\n"


# --- Executive summary ---


def _section_executive_summary(
    outputs: dict[str, str],
    signals: list[dict[str, object]],
) -> str:
    """Generate a narrative executive summary."""
    signal_count = sum(
        1 for s in signals if isinstance(s.get("state"), str) and s["state"] == "SIGNAL"
    )
    alert_count = sum(
        1 for s in signals if isinstance(s.get("state"), str) and s["state"] == "ALERT"
    )
    active_count = sum(
        1 for s in signals if isinstance(s.get("state"), str) and s["state"] == "ACTIVE"
    )

    best_confidence: ConfidenceScore | None = None
    signal_etfs = [
        s for s in signals if isinstance(s.get("state"), str) and s["state"] == "SIGNAL"
    ]
    if signal_etfs:
        best_confidence = _compute_signal_confidence(outputs, signal_etfs[0])

    favorable_factors: list[str] = []
    unfavorable_factors: list[str] = []
    if best_confidence:
        for f in best_confidence.factors:
            if f.assessment == FactorAssessment.FAVORABLE:
                favorable_factors.append(f.reason)
            elif f.assessment == FactorAssessment.UNFAVORABLE:
                unfavorable_factors.append(f.reason)

    lines: list[str] = []

    if signal_count > 0 and best_confidence:
        if best_confidence.level == ConfidenceLevel.HIGH:
            stance = "favor"
        elif best_confidence.level == ConfidenceLevel.MEDIUM:
            stance = "are mixed for"
        else:
            stance = "oppose"
        conf_str = f"{best_confidence.favorable_count}/{best_confidence.total_factors}"
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

    lines.append('<div class="kicker">Market Overview</div>')
    lines.append(f'<p class="headline">{html.escape(headline)}</p>')

    standfirst_parts: list[str] = []
    if signal_etfs:
        etf_mentions = []
        for s in signal_etfs[:3]:
            t = html.escape(str(s.get("leveraged_ticker", "?")))
            dd = s.get("underlying_drawdown_pct", 0)
            dd_s = _fmt_pct(dd) if isinstance(dd, (int, float)) else ""
            etf_mentions.append(
                f'<span class="highlight">{t} ({dd_s} drawdown)</span>',
            )
        standfirst_parts.append(
            " and ".join(etf_mentions) + " at actionable levels.",
        )

    if favorable_factors:
        support = html.escape(favorable_factors[0])
        standfirst_parts.append(f"Key support: {support}.")
    if unfavorable_factors:
        risk = html.escape(unfavorable_factors[0])
        standfirst_parts.append(f"Key risk: {risk}.")

    if standfirst_parts:
        lines.append(
            '<p class="detail">' + " ".join(standfirst_parts) + "</p>",
        )
    elif not signal_etfs:
        if favorable_factors:
            support = html.escape(favorable_factors[0])
            lines.append(f'<p class="detail">Key support: {support}</p>')
        if unfavorable_factors:
            risk = html.escape(unfavorable_factors[0])
            lines.append(f'<p class="detail">Key risk: {risk}</p>')

    if not lines:
        return ""
    return '<div class="exec-summary">\n' + "\n".join(lines) + "\n</div>\n"


# --- ETF signal cards ---


def _render_signal_card(
    outputs: dict[str, str],
    sig: dict[str, object],
) -> str:
    """Render a single ETF signal card with confidence drill-down."""
    ticker = html.escape(str(sig.get("leveraged_ticker", "?")))
    underlying = html.escape(str(sig.get("underlying_ticker", "")))
    state = str(sig.get("state", "?"))
    state_lower = state.lower()
    dd = sig.get("underlying_drawdown_pct", 0)
    dd_str = _fmt_pct(dd)
    ath = sig.get("underlying_ath")
    current = sig.get("underlying_current")
    pl = sig.get("current_pl_pct")
    entry_price = sig.get("leveraged_entry_price")
    target_pct = sig.get("profit_target_pct", 0.10)

    confidence = _compute_signal_confidence(outputs, sig)

    card_cls = f"signal-card signal-card-{state_lower}"
    parts: list[str] = [f'<div class="{card_cls}">']

    parts.append('<div class="signal-header">')
    parts.append(
        f'<span><span class="signal-ticker">{ticker}</span> '
        f"({underlying}) &mdash; {_badge(state)}</span>",
    )
    conf_badge = _confidence_badge(str(confidence.level))
    parts.append(
        f"<span>Confidence: {conf_badge} "
        f"({confidence.favorable_count}/{confidence.total_factors})"
        "</span>",
    )
    parts.append("</div>")

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
            f'P&L: <span class="{pl_cls}">{_fmt_pct(pl, signed=True)}</span>',
        )

    parts.append(
        '<div class="signal-details">' + " &bull; ".join(detail_parts) + "</div>",
    )

    parts.append(_render_confidence_dots(confidence))

    parts.append("<details>")
    parts.append("<summary>View 9-factor analysis</summary>")
    parts.append(_render_factor_table(confidence))
    parts.append("</details>")

    parts.append("</div>")
    return "\n".join(parts)


def _section_etf_signals(
    outputs: dict[str, str],
    signals: list[dict[str, object]],
) -> str:
    """Render ETF signals sorted by priority in a grid layout."""
    if not signals:
        return ""

    sorted_signals = sorted(
        signals[:10],
        key=lambda s: _STATE_PRIORITY.get(str(s.get("state", "")), 99),
    )

    actionable: list[str] = []
    approaching: list[str] = []
    monitoring: list[str] = []

    for sig in sorted_signals:
        if not isinstance(sig, dict):
            continue
        state = str(sig.get("state", ""))
        card = _render_signal_card(outputs, sig)
        if state in ("SIGNAL", "ACTIVE"):
            actionable.append(card)
        elif state == "ALERT":
            approaching.append(card)
        else:
            monitoring.append(card)

    result_parts: list[str] = []
    result_parts.append('<section id="signals">\n')
    result_parts.append(
        f"<h2>{_section_icon('signal')}Entry Signals &amp; Active Positions</h2>\n",
    )

    # Actionable + alert cards in grid
    grid_cards = actionable + approaching
    if grid_cards:
        result_parts.append('<div class="signal-grid">')
        result_parts.extend(grid_cards)
        result_parts.append("</div>")

    # Watch/monitoring collapsed
    if monitoring:
        result_parts.append(
            f"<details>\n<summary>{len(monitoring)} ETF(s) in monitoring state"
            "</summary>\n"
            '<div class="signal-grid">',
        )
        result_parts.extend(monitoring)
        result_parts.append("</div>\n</details>\n")

    result_parts.append("</section>\n")
    return "\n".join(result_parts)


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
            '<div class="sentiment-bar" role="img" '
            f'aria-label="Sentiment: {bullish} bullish, '
            f'{bearish} bearish, {neutral} neutral">'
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

        # Top headlines with links
        headlines = news.get("top_headlines", [])
        if isinstance(headlines, list) and headlines:
            parts.append('<p class="mt-12"><strong>Top headlines</strong></p>')
            parts.append('<ul class="headline-list">')
            seen_titles: set[str] = set()
            for h in headlines[:6]:
                if isinstance(h, dict):
                    raw_title = str(h.get("title", ""))
                    if raw_title in seen_titles:
                        continue
                    seen_titles.add(raw_title)
                    title = html.escape(raw_title)
                    link = str(h.get("link", ""))
                    source = html.escape(str(h.get("source", "")))
                    h_sent = str(h.get("sentiment", "")).upper()
                    if h_sent == "BEARISH":
                        marker = '<span class="hl-marker hl-bear">Bear</span>'
                    elif h_sent == "BULLISH":
                        marker = '<span class="hl-marker hl-bull">Bull</span>'
                    else:
                        marker = '<span class="hl-marker hl-neu">Neu</span>'
                    if link:
                        title_html = (
                            f'<a href="{html.escape(link)}" '
                            f'target="_blank" rel="noopener">{title}</a>'
                        )
                    else:
                        title_html = title
                    source_html = (
                        f'<span class="hl-source">{source}</span>' if source else ""
                    )
                    parts.append(f"<li>{marker}{title_html}{source_html}</li>")
            parts.append("</ul>")

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
                f'<p class="mt-12">Officials Tone: {_badge(tone)}',
            )
            if policy and policy != "N/A":
                parts.append(f" &nbsp; Policy: {_badge(policy)}")
            if isinstance(stmts, (int, float)) and stmts > 0:
                parts.append(
                    f' <span class="text-muted">({int(stmts)} statements)</span>',
                )
            parts.append("</p>")

    if not parts:
        return ""
    return (
        '<section id="sentiment">\n'
        f"<h2>{_section_icon('news')}Sentiment Analysis</h2>\n"
        '<div class="card">\n' + "\n".join(parts) + "\n</div>\n"
        "</section>\n"
    )


# --- Market conditions section ---


def _section_market_conditions(outputs: dict[str, str]) -> str:
    """Render market conditions: indices, risk indicators, commodities."""
    parts: list[str] = []

    stats = _parse_output(outputs.get("statistics.dashboard", ""))
    if isinstance(stats, dict):
        risk = stats.get("risk_indicators", {})
        if isinstance(risk, dict):
            assessment = str(risk.get("risk_assessment", "N/A"))
            parts.append(
                f"<p>Risk Assessment: {_badge(assessment)}</p>",
            )

            # Major indices — SPY, QQQ, DIA
            index_tiles: list[str] = []
            for ticker, name in [
                ("spy", "S&P 500"),
                ("qqq", "NASDAQ"),
                ("dia", "DOW"),
            ]:
                price = risk.get(f"{ticker}_price")
                chg = risk.get(f"{ticker}_change_1d_pct")
                if isinstance(price, (int, float)):
                    chg_html = ""
                    if isinstance(chg, (int, float)):
                        cls = _pct_class(chg)
                        chg_html = (
                            f'<div class="index-chg {cls}">'
                            f"{_fmt_pct(chg, signed=True)}</div>"
                        )
                    index_tiles.append(
                        '<div class="index-tile">'
                        f'<div class="index-name">{html.escape(name)}</div>'
                        f'<div class="index-price">{_fmt_price(price)}</div>'
                        f"{chg_html}</div>",
                    )
            if index_tiles:
                parts.append(
                    '<div class="index-tiles">' + "".join(index_tiles) + "</div>",
                )

            # Commodity tiles
            tiles: list[str] = []
            for asset, label in [
                ("gold", "Gold"),
                ("oil", "Oil"),
                ("dxy", "DXY"),
            ]:
                price = risk.get(f"{asset}_price")
                chg = risk.get(f"{asset}_change_5d_pct")
                if isinstance(price, (int, float)):
                    chg_html = ""
                    if isinstance(chg, (int, float)):
                        cls = _pct_class(chg)
                        chg_html = (
                            f'<div class="commodity-chg {cls}">'
                            f"{_fmt_pct(chg, signed=True)}</div>"
                        )
                    tiles.append(
                        '<div class="commodity-tile">'
                        f'<div class="commodity-name">{label}</div>'
                        f'<div class="commodity-price">{_fmt_price(price)}</div>'
                        f"{chg_html}</div>",
                    )
            if tiles:
                parts.append(
                    '<div class="commodity-tiles">' + "".join(tiles) + "</div>",
                )

        # Correlations
        corr = stats.get("correlations", {})
        if isinstance(corr, dict):
            decoupled = corr.get("decoupled_pairs", [])
            if isinstance(decoupled, list) and decoupled:
                pairs = ", ".join(html.escape(str(p)) for p in decoupled[:4])
                parts.append(
                    f'<p class="mt-8">'
                    f'<span class="badge badge-yellow">DECOUPLING</span> '
                    f"{pairs}</p>",
                )

    # Global central bank rates
    rates = _parse_output(outputs.get("macro.rates", ""))
    if isinstance(rates, dict):
        global_rates = rates.get("global_rates", {})
        if isinstance(global_rates, dict) and global_rates:
            bank_names: dict[str, str] = {
                "ecb": "ECB",
                "boe": "BOE",
                "boj": "BOJ",
                "boc": "BOC",
                "rba": "RBA",
            }
            rate_tiles: list[str] = []
            for bank, value in global_rates.items():
                name = bank_names.get(str(bank), str(bank).upper())
                if isinstance(value, (int, float)):
                    rate_tiles.append(
                        '<div class="rate-tile">'
                        f'<div class="rate-bank">{html.escape(name)}</div>'
                        f'<div class="rate-value">{value:.2f}%</div>'
                        "</div>",
                    )
            if rate_tiles:
                parts.append(
                    f'<p class="mt-16"><strong>'
                    f"{_section_icon('rates')}Global Central Bank Rates"
                    "</strong></p>",
                )
                parts.append(
                    '<div class="rates-grid">' + "".join(rate_tiles) + "</div>",
                )

    if not parts:
        return ""
    return (
        '<section id="market">\n'
        f"<h2>{_section_icon('conditions')}Market Conditions</h2>\n"
        '<div class="card">\n' + "\n".join(parts) + "\n</div>\n"
        "</section>\n"
    )


# --- Strategy section ---


def _section_strategy(outputs: dict[str, str]) -> str:
    """Render strategy backtest results with detailed analysis."""
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
        sharpe_str = f"{sharpe:.2f}" if isinstance(sharpe, (int, float)) else "N/A"
        wr = p.get("backtest_win_rate", None)
        wr_str = _fmt_pct(wr) if isinstance(wr, (int, float)) else "N/A"
        ret = p.get("backtest_total_return", None)
        ret_str = _fmt_pct(ret, signed=True) if isinstance(ret, (int, float)) else "N/A"
        ret_cls = _pct_class(ret)

        # Trade count
        trades = p.get("backtest_trade_count", None)
        trade_html = ""
        if isinstance(trades, (int, float)) and int(trades) > 0:
            n = int(trades)
            warn = " trade-count-warn" if n < 5 else ""
            trade_html = f'<span class="trade-count{warn}">{n}</span>'

        # Max drawdown
        max_dd = p.get("backtest_max_drawdown", None)
        max_dd_str = _fmt_pct(max_dd) if isinstance(max_dd, (int, float)) else ""

        # Average hold duration
        total_days = p.get("backtest_total_days", None)
        has_trades = isinstance(trades, (int, float)) and trades > 0
        trade_count = int(trades) if has_trades and trades is not None else 0
        avg_hold = ""
        if isinstance(total_days, (int, float)) and trade_count > 0:
            avg_hold = f"~{int(total_days / trade_count)}d"

        rows.append(
            f"<tr><td><strong>{ticker}</strong></td>"
            f"<td>{reason}</td>"
            f'<td class="num">{html.escape(sharpe_str)}</td>'
            f'<td class="num">{html.escape(wr_str)}</td>'
            f'<td class="num {ret_cls}">{html.escape(ret_str)}</td>'
            f'<td class="num">{trade_html}</td>'
            f'<td class="num">{html.escape(max_dd_str)}</td>'
            f'<td class="num">{html.escape(avg_hold)}</td></tr>',
        )

        # Entry/exit strategy detail row
        proposed_threshold = p.get("proposed_threshold", None)
        proposed_target = p.get("proposed_target", None)
        current_threshold = p.get("current_threshold", None)
        current_target = p.get("current_target", None)

        detail_parts: list[str] = []
        if isinstance(proposed_threshold, (int, float)):
            entry_str = f"buy at {proposed_threshold:.0%} drawdown from ATH"
            if isinstance(current_threshold, (int, float)):
                entry_str += f" (current: {current_threshold:.0%})"
            entry_esc = html.escape(entry_str)
            detail_parts.append(
                f'<span><span class="label">Entry:</span>'
                f" {entry_esc}</span>",
            )
        if isinstance(proposed_target, (int, float)):
            exit_str = f"+{proposed_target:.0%} profit target"
            if isinstance(current_target, (int, float)):
                exit_str += f" (current: +{current_target:.0%})"
            exit_esc = html.escape(exit_str)
            detail_parts.append(
                f'<span><span class="label">Exit:</span>'
                f" {exit_esc}</span>",
            )
        if avg_hold:
            hold_esc = html.escape(avg_hold)
            detail_parts.append(
                f'<span><span class="label">Avg Hold:</span>'
                f" {hold_esc}</span>",
            )
        if detail_parts:
            rows.append(
                '<tr><td colspan="8"><div class="strategy-entry-exit">'
                + "".join(detail_parts)
                + "</div></td></tr>",
            )

    if not rows:
        return ""

    # Extract analysis context from first proposal
    first = data[0] if isinstance(data[0], dict) else {}
    period = str(first.get("backtest_period", "2y"))
    avg_gain = first.get("backtest_avg_gain", None)
    avg_loss = first.get("backtest_avg_loss", None)

    analysis_parts: list[str] = [
        f"<p>Backtests run over <strong>{html.escape(period)}</strong> "
        "of historical data. Strategy optimizer tests entry thresholds "
        "(3-15%) and profit targets (8-15%) to find optimal parameters "
        "for each ETF based on Sharpe ratio.</p>",
    ]
    if isinstance(avg_gain, (int, float)) or isinstance(avg_loss, (int, float)):
        note_parts: list[str] = []
        if isinstance(avg_gain, (int, float)):
            note_parts.append(f"avg gain {_fmt_pct(avg_gain, signed=True)}")
        if isinstance(avg_loss, (int, float)):
            note_parts.append(f"avg loss {_fmt_pct(avg_loss, signed=True)}")
        analysis_parts.append(
            f'<p class="text-muted" style="font-size:13px">'
            f"Reference: {', '.join(note_parts)} per trade.</p>",
        )

    return (
        f'<section id="strategy">\n'
        f"<h2>{_section_icon('strategy')}Strategy Backtest Results</h2>\n"
        '<div class="card">\n' + "\n".join(analysis_parts) + '\n<table class="mt-12">\n'
        "<thead><tr>"
        '<th scope="col">ETF</th><th scope="col">Proposal</th>'
        '<th scope="col">Sharpe</th><th scope="col">Win Rate</th>'
        '<th scope="col">Return</th><th scope="col">Trades</th>'
        '<th scope="col">Max DD</th><th scope="col">Avg Hold</th>'
        "</tr></thead>\n<tbody>\n" + "\n".join(rows) + "\n</tbody></table>\n"
        "</div>\n</section>\n"
    )


# --- Geopolitical detail section ---


def _section_geopolitical(outputs: dict[str, str]) -> str:
    """Render geopolitical events detail with links and affected sectors."""
    geo = _parse_output(outputs.get("geopolitical.summary", ""))
    if not isinstance(geo, dict):
        return ""

    parts: list[str] = []

    risk = str(geo.get("risk_level", "N/A"))
    total = geo.get("total_events", 0)
    high = geo.get("high_impact_count", 0)

    parts.append(
        f"<p>Risk Level: {_badge(risk)} &mdash; "
        f"{html.escape(str(total))} events tracked"
        f" ({html.escape(str(high))} high-impact)</p>",
    )

    # Affected sectors
    sectors = geo.get("affected_sectors", {})
    if isinstance(sectors, dict) and sectors:
        sorted_sectors = sorted(
            sectors.items(),
            key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
            reverse=True,
        )
        parts.append('<div class="sector-badges">')
        for name, count in sorted_sectors[:8]:
            parts.append(
                f'<span class="sector-badge">{html.escape(str(name))} ({count})</span>',
            )
        parts.append("</div>")

    # Events by category
    cats = geo.get("events_by_category", {})
    if isinstance(cats, dict) and cats:
        cat_parts = []
        for cat, count in sorted(
            cats.items(),
            key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
            reverse=True,
        ):
            cat_parts.append(
                f'<span class="badge badge-gray">'
                f"{html.escape(str(cat))} ({count})</span>",
            )
        parts.append(
            f'<p class="mt-8">{" ".join(cat_parts)}</p>',
        )

    # Top events with links
    top_events = geo.get("top_events", [])
    if isinstance(top_events, list) and top_events:
        parts.append('<div class="geo-events">')
        for ev in top_events[:5]:
            if not isinstance(ev, dict):
                continue
            raw_title = str(ev.get("title", ""))
            title = html.escape(raw_title)
            url = str(ev.get("url", ""))
            impact = str(ev.get("impact", ""))
            category = html.escape(str(ev.get("category", "")))
            ev_sectors = ev.get("affected_sectors", ev.get("sectors", []))
            sector_str = (
                ", ".join(html.escape(str(s)) for s in ev_sectors)
                if isinstance(ev_sectors, (list, tuple))
                else ""
            )

            if url:
                title_html = (
                    f'<a href="{html.escape(url)}" '
                    f'target="_blank" rel="noopener">{title}</a>'
                )
            else:
                title_html = title

            parts.append('<div class="geo-event">')
            parts.append(
                f'<div class="geo-title">{_badge(impact)} {title_html}</div>',
            )
            meta_parts = []
            if category:
                meta_parts.append(category)
            if sector_str:
                meta_parts.append(f"Sectors: {sector_str}")
            if meta_parts:
                parts.append(
                    f'<div class="geo-meta">{" &bull; ".join(meta_parts)}</div>',
                )
            parts.append("</div>")
        parts.append("</div>")

    if not parts:
        return ""
    return (
        '<section id="geopolitical">\n'
        f"<h2>{_section_icon('globe')}Geopolitical Risk</h2>\n"
        '<div class="card">\n' + "\n".join(parts) + "\n</div>\n"
        "</section>\n"
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
    status_cls = "badge-green" if run.failed == 0 else "badge-red"
    return (
        '<section id="modules">\n'
        "<details>\n"
        "<summary>"
        '<h2 style="display:inline">Module Status</h2> '
        f'<span class="badge {status_cls}">'
        f"{run.succeeded}/{run.total_modules}</span>"
        "</summary>\n"
        '<div class="card">\n'
        '<div class="module-grid">\n' + "\n".join(pills) + "\n</div>\n</div>\n"
        "</details>\n"
        "</section>\n"
    )


# --- Page builders ---


def _section_strategy_research(outputs: dict[str, str]) -> str:
    """Render strategy research section summarizing optimization exploration."""
    data = _parse_output(outputs.get("strategy.proposals", ""))
    if not isinstance(data, list) or not data:
        return ""

    # Gather unique thresholds and targets tested
    thresholds: set[float] = set()
    targets: set[float] = set()
    tickers: list[str] = []
    for p in data:
        if not isinstance(p, dict):
            continue
        t = p.get("proposed_threshold")
        if isinstance(t, (int, float)):
            thresholds.add(t)
        tg = p.get("proposed_target")
        if isinstance(tg, (int, float)):
            targets.add(tg)
        tk = str(p.get("leveraged_ticker", ""))
        if tk and tk not in tickers:
            tickers.append(tk)

    if not tickers:
        return ""

    parts: list[str] = [
        '<p class="kicker">Strategy Research</p>',
        "<p>The strategy optimizer explored "
        f"<strong>{len(tickers)} ETF(s)</strong> testing "
        "entry thresholds from 3% to 15% and profit targets from 8% to 15%. "
        "Results are ranked by risk-adjusted returns (Sharpe ratio).</p>",
    ]

    if thresholds:
        sorted_t = sorted(thresholds)
        t_range = f"{sorted_t[0]:.0%}&ndash;{sorted_t[-1]:.0%}"
        parts.append(
            f'<p class="mt-8">Optimal entries found in the '
            f"<strong>{t_range}</strong> drawdown range</p>",
        )

    if targets:
        sorted_tg = sorted(targets)
        tg_range = f"+{sorted_tg[0]:.0%}&ndash;+{sorted_tg[-1]:.0%}"
        parts.append(
            f"<p>Optimal profit targets in the <strong>{tg_range}</strong> range</p>",
        )

    etf_badges = " ".join(
        f'<span class="sector-badge">{html.escape(t)}</span>' for t in tickers[:8]
    )
    parts.append(f'<div class="sector-badges mt-8">{etf_badges}</div>')

    return (
        '<section id="research">\n'
        f"<h2>{_section_icon('strategy')}Strategy Research</h2>\n"
        '<div class="card">\n' + "\n".join(parts) + "\n</div>\n"
        "</section>\n"
    )


def _nav_menu() -> str:
    """Render the sticky navigation menu."""
    links = [
        ("#signals", "Signals"),
        ("#sentiment", "Sentiment"),
        ("#market", "Market"),
        ("#geopolitical", "Geopolitical"),
        ("#strategy", "Strategy"),
        ("#research", "Research"),
        ("#modules", "Modules"),
    ]
    items = "".join(f'<a href="{href}">{label}</a>' for href, label in links)
    return f'<nav class="nav-menu" aria-label="Report sections">{items}</nav>\n'


def build_html_report(
    run: SchedulerRun,
    *,
    date: str = "",
) -> str:
    """Build a complete narrative HTML dashboard from a scheduler run."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    outputs: dict[str, str] = {}
    for result in run.results:
        if result.success and result.output.strip():
            outputs[result.name] = result.output.strip()

    signals_data = _parse_output(outputs.get("etf.signals", ""))
    signals: list[dict[str, object]] = []
    if isinstance(signals_data, list):
        signals = [s for s in signals_data if isinstance(s, dict)]

    exec_summary = _section_executive_summary(outputs, signals)
    kpi = _section_kpi_strip(outputs)
    signal_cards = _section_etf_signals(outputs, signals)
    sentiment = _section_sentiment(outputs)
    conditions = _section_market_conditions(outputs)
    geopolitical = _section_geopolitical(outputs)
    strategy = _section_strategy(outputs)
    research = _section_strategy_research(outputs)
    modules = _section_module_status(run)

    masthead = (
        '<div class="masthead">\n'
        "<h1>The Swing Trading Report</h1>\n"
        '<div class="masthead-meta">Leveraged ETF Analysis<br>'
        "Mean-Reversion System</div>\n"
        "</div>\n"
        '<div class="masthead-rule"></div>\n'
    )

    nav = _nav_menu()

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; {html.escape(report_time)}</span>\n"
        '<div class="header-status">'
        f'<span class="ok">{run.succeeded}</span>/{run.total_modules} OK'
        f' &bull; <span class="fail">{run.failed}</span> failed'
        "</div>\n</header>\n"
    )

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
            mid = conditions + sentiment

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "not financial advice.</span>\n"
        '<span><a href="../index.html">All Reports</a></span>\n'
        "</footer>\n"
    )

    body_parts = [
        masthead,
        nav,
        header,
        '<main id="main-content">\n',
        exec_summary,
        kpi,
        signal_cards,
        mid,
        geopolitical,
        strategy,
        research,
        modules,
        "</main>\n",
        footer,
    ]
    return _html_page(
        title=f"Dashboard {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"Daily leveraged ETF swing trading dashboard for {report_date}",
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
        '<div class="report-list">\n' + "\n".join(cards) + "\n</div>" if cards else ""
    )

    body = (
        '<div class="masthead">\n'
        "<h1>The Swing Trading Report</h1>\n"
        '<div class="masthead-meta">Leveraged ETF Analysis<br>'
        "Report Archive</div>\n"
        "</div>\n"
        '<div class="masthead-rule"></div>\n'
        '<header class="header">\n'
        f"<span>{len(report_dates)} report(s)</span>\n"
        "</header>\n"
        f'<main id="main-content">\n{list_html}\n</main>\n'
        '<footer class="footer">\n'
        '<span>Powered by <a href="https://github.com/bikoman57/claude">'
        "fin-agents</a></span>\n</footer>"
    )
    return _html_page(
        title="Trading Reports",
        body=body,
        description="Leveraged ETF swing trading dashboard reports",
    )

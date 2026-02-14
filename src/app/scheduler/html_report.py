"""HTML report generation for GitHub Pages — narrative dashboard layout."""

from __future__ import annotations

import html
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from app.agile.store import (
    get_current_sprint,
    list_retros,
    list_standups,
    load_retro,
    load_roadmap,
    load_standup,
)
from app.devops.health import get_all_module_health, get_system_health
from app.etf.confidence import (
    ConfidenceLevel,
    ConfidenceScore,
    FactorAssessment,
    FactorResult,
    assess_drawdown_depth,
    assess_earnings_risk,
    assess_fed_regime,
    assess_fundamentals_health,
    assess_geopolitical_risk,
    assess_market_statistics,
    assess_news_sentiment,
    assess_prediction_markets,
    assess_social_sentiment,
    assess_vix_regime,
    assess_yield_curve,
    compute_confidence,
)
from app.scheduler.runner import SchedulerRun

_ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

_CSS = """\
/* === Dark Fintech Dashboard Design === */
:root {
  --bg-primary: #131722;
  --bg-secondary: #1e2433;
  --bg-tertiary: #252b3b;
  --bg-dark: #0b0f18;
  --border-primary: #2a3346;
  --border-light: #232b3e;
  --border-hover: #58a6ff;
  --text-primary: #e6edf3;
  --text-secondary: #c9d1d9;
  --text-muted: #8b949e;
  --accent: #58a6ff;
  --accent-light: #1a2744;
  --success: #3fb950;
  --success-bg: #0d2818;
  --warning: #d29922;
  --warning-bg: #2a1f00;
  --danger: #f85149;
  --danger-bg: #2d0a0a;
  --info: #58a6ff;
  --info-bg: #0d1f3c;
  --purple: #bc8cff;
  --purple-bg: #1f0d3c;
  --neutral: #484f58;
  --font-serif: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
  padding-bottom: 8px; border-bottom: 2px solid var(--border-primary);
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

/* Top bar — unified navy header with navigation */
.top-bar { background: var(--bg-dark); color: #fff;
  padding: 0 clamp(16px, 3vw, 48px);
  margin: 0 calc(-1 * clamp(16px, 3vw, 48px));
  display: flex; align-items: center;
  position: sticky; top: 0; z-index: 100;
  min-height: 56px; flex-wrap: wrap; }
.top-bar h1 { color: #fff; font-size: 16px; font-weight: 600;
  letter-spacing: -0.01em; white-space: nowrap; margin-right: 24px; }
.top-bar-logo { height: 40px; width: auto; vertical-align: middle;
  margin-right: 12px; border-radius: 4px; }

/* Navigation menu */
.nav-menu { display: flex; gap: 0; align-items: center; }
.nav-menu a { font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
  color: rgba(255,255,255,0.65); white-space: nowrap;
  padding: 18px 14px; border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s; }
.nav-menu a:hover, .nav-menu a:focus { color: #fff;
  border-bottom-color: #fff; text-decoration: none; }
.nav-menu a.nav-active { color: #fff;
  border-bottom-color: #fff; }
.nav-dropdown-btn.nav-active { color: #fff;
  border-bottom: 2px solid #fff; }
.nav-menu .nav-divider { width: 1px; background: rgba(255,255,255,0.2);
  margin: 12px 0; flex-shrink: 0; }

/* Section dropdown */
.nav-dropdown { position: relative; }
.nav-dropdown-btn { font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
  color: rgba(255,255,255,0.65); background: none; border: none;
  padding: 18px 14px; cursor: pointer; white-space: nowrap;
  display: flex; align-items: center; gap: 6px;
  transition: color 0.15s; }
.nav-dropdown-btn:hover, .nav-dropdown-btn:focus { color: #fff; outline: none; }
.nav-dropdown-btn::after { content: "\\25BC"; font-size: 0.6em;
  transition: transform 0.15s ease; }
.nav-dropdown.open .nav-dropdown-btn::after { transform: rotate(180deg); }
.nav-dropdown-btn:hover, .nav-dropdown.open .nav-dropdown-btn { color: #fff; }
.nav-dropdown-menu { display: none; position: absolute; top: 100%;
  right: 0; background: var(--bg-dark); border: 1px solid rgba(255,255,255,0.15);
  border-radius: 6px; padding: 6px 0; min-width: 180px; z-index: 200;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
.nav-dropdown.open .nav-dropdown-menu { display: block; }
.nav-dropdown-menu a { display: block; padding: 10px 18px;
  border-bottom: none; font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
  color: rgba(255,255,255,0.65); text-decoration: none;
  transition: background 0.1s, color 0.1s; }
.nav-dropdown-menu a:hover, .nav-dropdown-menu a:focus {
  background: rgba(255,255,255,0.08); color: #fff;
  border-bottom: none; text-decoration: none; }

/* Summary link cards (dashboard → sub-page teasers) */
.summary-link-card { display: block; padding: 16px 20px;
  background: var(--bg-secondary); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px; text-decoration: none; transition: border-color 0.15s;
  margin-bottom: 12px; }
.summary-link-card:hover { border-color: rgba(255,255,255,0.2);
  text-decoration: none; }
.summary-link-card .card-title { font-family: var(--font-serif);
  font-size: 15px; font-weight: 700; color: var(--text-primary); }
.summary-link-card .card-detail { font-size: 13px;
  color: var(--text-muted); margin-top: 4px; }
.summary-link-card .card-cta { font-family: var(--font-mono);
  font-size: 11px; color: var(--accent); margin-top: 8px;
  text-transform: uppercase; letter-spacing: 0.08em; }

/* Report date picker */
.nav-date-picker { font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
  color: rgba(255,255,255,0.65); background: transparent;
  border: 1px solid rgba(255,255,255,0.25); border-radius: 4px;
  padding: 6px 10px; margin: 0 8px; cursor: pointer;
  appearance: auto; }
.nav-date-picker:hover, .nav-date-picker:focus {
  color: #fff; border-color: rgba(255,255,255,0.5);
  outline: none; }
.nav-date-picker option { background: var(--bg-dark); color: #fff; }

/* Header / datebar */
.header { display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid var(--border-primary); padding: 12px 0;
  margin-bottom: 28px; flex-wrap: wrap; gap: 8px;
  font-size: 13px; color: var(--text-muted); }
.header-status { font-size: 0.9em; font-family: var(--font-sans);
  color: var(--text-secondary); }

/* Executive summary / lede */
.exec-summary { margin-bottom: 32px; padding-bottom: 28px;
  border-bottom: 1px solid var(--border-primary); }
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
  border-radius: 10px; position: relative; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.kpi-card::before { content: ''; position: absolute; left: 0; top: 0;
  width: 100%; height: 3px; }
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
  padding: 24px; margin-bottom: 24px; border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06); }

/* Grid layouts */
.grid-2col { display: grid; grid-template-columns: 1.4fr 1fr; gap: 32px; }

/* Badges */
.badge { display: inline-block; padding: 3px 10px; border-radius: 12px;
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.06em; text-transform: uppercase; }
.badge-green { background: var(--success-bg); color: var(--success); }
.badge-yellow { background: var(--warning-bg); color: var(--warning); }
.badge-red { background: var(--danger-bg); color: var(--danger); }
.badge-gray { background: var(--bg-tertiary); color: var(--text-muted); }
.badge-blue { background: var(--info-bg); color: var(--info); }

/* Tables */
table { border-collapse: collapse; width: 100%; }
th { font-family: var(--font-mono); text-align: left; padding: 12px 14px;
  color: var(--text-secondary); font-weight: 600; font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.08em;
  background: var(--bg-tertiary); border-bottom: 2px solid var(--border-primary); }
td { padding: 12px 14px; border-bottom: 1px solid var(--border-light); }
tbody tr:nth-child(even) { background: #1a2030; }
tbody tr:hover { background: #252d40; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
th.num { text-align: right; }
.pct-up { color: var(--success); }
.pct-down { color: var(--danger); }

/* Signal cards — grid layout */
.signal-grid { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 16px; margin-bottom: 16px; }
.signal-card { background: var(--bg-secondary); border: 1px solid var(--border-light);
  padding: 16px 20px; border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06); position: relative;
  overflow: hidden; }
.signal-card::before { content: ''; position: absolute; left: 0; top: 0;
  width: 100%; height: 3px; background: var(--border-light); }
.signal-card-signal::before { background: var(--success); }
.signal-card-signal { border-color: var(--success); }
.signal-card-signal .signal-ticker { font-size: 1.35em; }
.signal-card-alert::before { background: var(--warning); }
.signal-card-active::before { background: var(--info); }
.signal-card-watch::before { background: var(--neutral); }
.signal-card-target::before { background: var(--purple); }
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

/* Congress member cards */
.congress-grid { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px; margin-top: 12px; }
.congress-member { background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  padding: 14px 18px; border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.congress-member-name { font-family: var(--font-serif); font-size: 14px;
  font-weight: 700; color: var(--text-primary); }
.congress-member-meta { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); margin-top: 4px; }
.tier-a { border-left: 3px solid var(--success); }
.tier-b { border-left: 3px solid var(--info); }
.tier-c { border-left: 3px solid var(--neutral); }
.tier-d, .tier-f { border-left: 3px solid var(--danger); }

/* Standfirst highlight */
.highlight { background: var(--accent-light);
  padding: 1px 4px; border-radius: 2px; }

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
  border-top: 1px solid var(--border-primary); font-size: 12px;
  color: var(--text-muted); display: flex; justify-content: space-between;
  flex-wrap: wrap; gap: 8px; }
a { color: var(--accent); text-decoration: none; font-weight: 600; }
a:hover { text-decoration: underline; }
.ok { color: var(--success); }
.fail { color: var(--danger); }

/* === Report Page — Compact Financial Layout === */
.rpt-compact .exec-summary { margin-bottom: 12px; padding-bottom: 10px; }
.rpt-compact .exec-summary .headline { font-size: 20px; line-height: 1.25; }
.rpt-compact .exec-summary .detail { font-size: 13px; line-height: 1.5; }
.rpt-compact .kpi-strip { gap: 8px; margin-bottom: 0;
  padding-bottom: 12px; border-bottom: 1px solid var(--border-primary); }
.rpt-compact .kpi-card { padding: 10px 12px; border-radius: 6px; }
.rpt-compact .kpi-value { font-size: 20px; }
.rpt-compact .kpi-icon .material-symbols-outlined { font-size: 18px; }
.rpt-compact .kpi-sub { font-size: 11px; margin-top: 2px; }
.rpt-compact .kpi-label { font-size: 9px; }
.rpt-compact .kpi-icon { margin-bottom: 4px; }
.rpt-layout { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
  align-items: start; margin-top: 12px; }
.rpt-main { }
.rpt-sidebar { }
.rpt-compact section { padding: 12px 0;
  border-bottom: 1px solid var(--border-primary); }
.rpt-compact section:last-child { border-bottom: none; }
.rpt-compact h2 { font-size: 15px; margin-bottom: 8px; padding-bottom: 4px;
  border-bottom-width: 1px; }
.rpt-compact .card { padding: 0; margin-bottom: 0; border: none; border-radius: 0;
  box-shadow: none; background: transparent; }
.rpt-compact .signal-grid { grid-template-columns: 1fr;
  gap: 6px; margin-bottom: 6px; }
.rpt-compact .signal-card { padding: 8px 10px; border-radius: 4px; }
.rpt-compact .signal-header { margin-bottom: 2px; }
.rpt-widget .signal-grid { gap: 4px; margin-bottom: 4px; }
.rpt-widget .signal-card { padding: 6px 8px; border-radius: 4px; font-size: 12px; }
.rpt-widget .signal-card::before { width: 3px; }
.rpt-widget .signal-ticker { font-size: 13px !important; }
.rpt-widget .signal-header { margin-bottom: 1px; gap: 4px; }
.rpt-widget .signal-badge { font-size: 9px; padding: 1px 6px; }
.rpt-widget .signal-details { font-size: 11px; gap: 2px; }
.rpt-widget .signal-details .grid-2col { gap: 2px; }
.rpt-widget .confidence-drilldown { font-size: 10px; padding: 4px 0 0; }
.rpt-widget .confidence-drilldown summary { font-size: 10px; }
.rpt-widget details.watch-group { font-size: 11px; }
.rpt-widget details.watch-group summary { padding: 4px 0; }
.rpt-compact .grid-2col { gap: 0; grid-template-columns: 1fr; }

/* Sidebar widgets */
.rpt-widget { background: var(--bg-secondary); border: 1px solid var(--border-light);
  border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.rpt-widget:last-child { margin-bottom: 0; }
.rpt-widget-title { font-family: var(--font-mono); font-size: 11px; font-weight: 700;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em;
  padding-bottom: 8px; border-bottom: 1px solid var(--border-primary);
  margin-bottom: 8px; }
.rpt-widget section { padding: 0 !important; border-bottom: none !important; }
.rpt-widget section h2 { display: none; }
.rpt-widget .card { padding: 0; margin: 0; border: none;
  border-radius: 0; box-shadow: none; background: transparent; }
.rpt-widget .kpi-strip { grid-template-columns: repeat(2, 1fr);
  gap: 6px; margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
.rpt-widget .kpi-card { padding: 8px 10px; }
.rpt-widget .kpi-value { font-size: 16px; }
.rpt-widget .kpi-icon { margin-bottom: 2px; }
.rpt-widget .kpi-icon .material-symbols-outlined { font-size: 16px; }
.rpt-widget .kpi-label { font-size: 8px; }
.rpt-widget .kpi-sub { font-size: 10px; margin-top: 2px; }
.rpt-widget .gauge-track { margin-top: 6px; }
.rpt-widget .index-tiles { gap: 6px; margin-bottom: 8px; }
.rpt-widget .index-tile { padding: 8px; border-radius: 4px; }
.rpt-widget .index-price { font-size: 16px; }
.rpt-widget .index-chg { font-size: 11px; }
.rpt-widget .commodity-tiles { gap: 6px; }
.rpt-widget .commodity-tile { padding: 8px; }
.rpt-widget .commodity-price { font-size: 16px; }
.rpt-widget .commodity-chg { font-size: 11px; }
.rpt-widget .rates-grid { gap: 4px; }
.rpt-widget .rate-tile { padding: 6px; }
.rpt-widget .rate-value { font-size: 14px; }
.rpt-widget .headline-list li { padding: 6px 0; font-size: 13px; }
.rpt-widget .geo-event { padding: 6px 0; }
.rpt-widget .geo-title { font-size: 13px; }
.rpt-widget .sentiment-bar { height: 8px; margin: 6px 0; }
.rpt-widget .sentiment-counts { font-size: 10px; gap: 10px; }
.rpt-widget .sector-badges { margin-top: 6px; }
.rpt-compact table th { padding: 6px 8px; font-size: 9px; }
.rpt-compact table td { padding: 6px 8px; font-size: 12px; }
.rpt-compact .strategy-entry-exit { padding: 4px 8px; font-size: 11px; }
.rpt-compact .module-pill { font-size: 9px; padding: 2px 8px; }
.rpt-compact .footer { margin-top: 16px; padding: 12px 0; }

/* === Index Page — Compact Dashboard === */
.idx-ticker-bar { display: flex; gap: 0; align-items: stretch;
  background: var(--bg-dark); border-bottom: 1px solid var(--border-primary);
  margin: 0 calc(-1 * clamp(16px, 3vw, 48px));
  padding: 0 clamp(16px, 3vw, 48px); overflow-x: auto; }
.idx-ticker { display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 8px 16px; min-width: 80px;
  border-right: 1px solid var(--border-primary);
  font-family: var(--font-mono); font-size: 11px; line-height: 1.3; }
.idx-ticker:last-child { border-right: none; }
.idx-ticker .tk-sym { font-weight: 700; color: var(--text-primary);
  font-size: 12px; }
.idx-ticker .tk-sector { color: var(--text-muted); font-size: 9px;
  text-transform: uppercase; letter-spacing: 0.06em; }
.idx-layout { display: grid; grid-template-columns: 1fr 280px;
  gap: 0; margin-top: 0; min-height: 60vh; }
.idx-main { border-right: 1px solid var(--border-primary);
  padding-right: 24px; }
.idx-sidebar { padding-left: 20px; }

/* Featured latest report */
.idx-featured { padding: 20px 0 16px; border-bottom: 1px solid var(--border-primary); }
.idx-featured-kicker { font-family: var(--font-mono); font-size: 10px;
  font-weight: 700; color: var(--accent); text-transform: uppercase;
  letter-spacing: 0.12em; margin-bottom: 6px; }
.idx-featured h2 { font-size: 22px; font-weight: 700; margin-bottom: 6px;
  padding-bottom: 0; border-bottom: none; display: block; line-height: 1.3; }
.idx-featured h2 a { color: var(--text-primary); }
.idx-featured h2 a:hover { color: var(--accent); }
.idx-featured-meta { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); margin-bottom: 8px; }
.idx-featured-tabs { display: flex; gap: 0; flex-wrap: wrap; margin-top: 10px; }
.idx-tab { font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em; padding: 5px 12px;
  color: var(--text-muted); border: 1px solid var(--border-primary);
  border-right: none; background: var(--bg-secondary);
  transition: color 0.1s, background 0.1s; }
.idx-tab:last-child { border-right: 1px solid var(--border-primary); }
.idx-tab:first-child { border-radius: 4px 0 0 4px; }
.idx-tab:last-child { border-radius: 0 4px 4px 0; }
.idx-tab:hover { color: var(--text-primary); background: var(--bg-tertiary);
  text-decoration: none; }

/* Report row items */
.idx-report-row { display: flex; align-items: center; gap: 12px;
  padding: 12px 0; border-bottom: 1px solid var(--border-light); }
.idx-report-row:last-child { border-bottom: none; }
.idx-report-date { font-family: var(--font-serif); font-size: 15px;
  font-weight: 600; white-space: nowrap; }
.idx-report-date a { color: var(--text-primary); }
.idx-report-date a:hover { color: var(--accent); }
.idx-report-pages { display: flex; gap: 6px; flex-wrap: wrap; }
.idx-page-link { font-family: var(--font-mono); font-size: 9px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
  padding: 2px 7px; background: var(--bg-tertiary); color: var(--text-muted);
  border-radius: 3px; transition: color 0.1s, background 0.1s; }
.idx-page-link:hover { color: var(--text-primary); background: var(--bg-secondary);
  text-decoration: none; }

/* Sidebar sections */
.idx-sb-section { padding: 14px 0; border-bottom: 1px solid var(--border-primary); }
.idx-sb-section:last-child { border-bottom: none; }
.idx-sb-title { font-family: var(--font-mono); font-size: 11px;
  font-weight: 700; color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.1em; margin-bottom: 10px; }

/* Sidebar archive list */
.idx-archive-item { display: flex; justify-content: space-between;
  align-items: center; padding: 7px 0;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px; }
.idx-archive-item:last-child { border-bottom: none; }
.idx-archive-item a { color: var(--text-secondary); font-weight: 500; }
.idx-archive-item a:hover { color: var(--accent); }
.badge-latest { background: var(--accent); color: #fff; font-size: 9px;
  font-family: var(--font-mono); padding: 1px 6px;
  text-transform: uppercase; letter-spacing: 0.06em; border-radius: 2px; }

/* Sidebar ETF watchlist */
.idx-etf-row { display: flex; justify-content: space-between;
  align-items: center; padding: 5px 0;
  border-bottom: 1px solid var(--border-light); font-size: 12px; }
.idx-etf-row:last-child { border-bottom: none; }
.idx-etf-sym { font-family: var(--font-mono); font-weight: 700;
  color: var(--text-primary); font-size: 12px; }
.idx-etf-name { color: var(--text-muted); font-size: 11px; }

/* Section header on index page */
.idx-section-head { font-family: var(--font-mono); font-size: 11px;
  font-weight: 700; color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.1em; padding: 14px 0 8px;
  border-bottom: 1px solid var(--border-primary); margin-bottom: 0; }

/* Focus-visible */
a:focus-visible, summary:focus-visible {
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
  .idx-layout { grid-template-columns: 1fr; }
  .idx-main { border-right: none; padding-right: 0; }
  .idx-sidebar { padding-left: 0; border-top: 1px solid var(--border-primary); }
  .rpt-layout { grid-template-columns: repeat(2, 1fr); }
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
  .rpt-layout { grid-template-columns: 1fr; }
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
  .top-bar { background: #000; color: #fff; }
  .card, .signal-card, .kpi-card, .exec-summary, .report-card {
    background: #fff; border-color: #ccc; box-shadow: none;
    break-inside: avoid; color: #000; }
  .skip-nav, .top-bar { display: none; }
  details[open] > summary { display: none; }
  details > *:not(summary) { display: block !important; }
  details:not([open]) { display: block; }
  details:not([open]) > *:not(summary) { display: block !important; }
  details:not([open]) > summary { display: none; }
  .badge { border: 1px solid currentColor; }
  a { color: #000; text-decoration: underline; }
  .footer { page-break-before: auto; }
  .report-card:hover { transform: none; }
  h1, h2, .kpi-value, .signal-ticker { color: #000; }
}

/* === Company Page Styles === */

/* Kanban board */
.kanban-board { display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 12px; margin-top: 12px; }
@media (max-width: 900px) { .kanban-board { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .kanban-board { grid-template-columns: 1fr; } }
.kanban-column { background: var(--bg-secondary); border-radius: 8px;
  padding: 12px; border: 1px solid var(--border-primary); min-height: 120px; }
.kanban-column h3 { font-size: 13px; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 10px;
  padding-bottom: 6px; border-bottom: 2px solid var(--border-primary); }
.kanban-card { background: var(--bg-tertiary); border-radius: 6px;
  padding: 10px 12px; margin-bottom: 8px; border-left: 3px solid var(--accent);
  font-size: 13px; line-height: 1.4; }
.kanban-card .task-id { font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted); }
.kanban-card .task-title { color: var(--text-primary); margin: 4px 0; }
.kanban-card .task-dept { font-size: 11px; color: var(--text-muted); }
.kanban-card.priority-critical { border-left-color: var(--danger); }
.kanban-card.priority-high { border-left-color: var(--warning); }
.kanban-card.priority-medium { border-left-color: var(--accent); }
.kanban-card.priority-low { border-left-color: var(--text-muted); }

/* Progress bars for OKRs and budgets */
.progress-bar { height: 8px; border-radius: 4px; background: var(--bg-tertiary);
  overflow: hidden; margin-top: 6px; }
.progress-fill { height: 100%; border-radius: 4px; min-width: 2px; }
.progress-fill.green { background: var(--success); }
.progress-fill.yellow { background: var(--warning); }
.progress-fill.red { background: var(--danger); }

/* OKR cards */
.okr-card { background: var(--bg-secondary); border-radius: 8px;
  padding: 16px; margin-bottom: 12px; border: 1px solid var(--border-primary); }
.okr-card h3 { font-size: 15px; color: var(--text-primary); margin-bottom: 8px; }
.okr-card .okr-id { font-family: var(--font-mono); font-size: 12px;
  color: var(--accent); margin-right: 8px; }
.okr-card .kr-list { list-style: none; padding: 0; margin: 8px 0 0 0; }
.okr-card .kr-list li { font-size: 13px; color: var(--text-secondary);
  padding: 3px 0; padding-left: 20px; position: relative; }
.okr-card .kr-list li::before { content: "\\2022"; position: absolute;
  left: 6px; color: var(--text-muted); }
.okr-pct { font-family: var(--font-mono); font-size: 13px;
  color: var(--text-muted); float: right; }

/* Health grid */
.health-grid { display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px; margin-top: 12px; }
.health-card { background: var(--bg-secondary); border-radius: 8px;
  padding: 14px; border: 1px solid var(--border-primary); }
.health-card .module-name { font-family: var(--font-mono); font-size: 13px;
  color: var(--text-primary); margin-bottom: 6px; }
.health-card .health-stat { font-size: 12px; color: var(--text-muted);
  display: flex; justify-content: space-between; padding: 2px 0; }
.health-card .health-stat .val { color: var(--text-secondary);
  font-family: var(--font-mono); }
.health-card.trend-improving { border-left: 3px solid var(--success); }
.health-card.trend-stable { border-left: 3px solid var(--text-muted); }
.health-card.trend-degrading { border-left: 3px solid var(--danger); }

/* Grade badge */
.grade-badge { display: inline-block; font-size: 28px; font-weight: 700;
  font-family: var(--font-mono); width: 48px; height: 48px; line-height: 48px;
  text-align: center; border-radius: 8px; }
.grade-A { background: var(--success-bg); color: var(--success); }
.grade-B { background: var(--info-bg); color: var(--info); }
.grade-C { background: var(--warning-bg); color: var(--warning); }
.grade-D, .grade-F { background: var(--danger-bg); color: var(--danger); }

/* Ceremony sections */
.ceremony-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
@media (max-width: 900px) { .ceremony-grid { grid-template-columns: 1fr; } }
.ceremony-col { background: var(--bg-secondary); border-radius: 8px;
  padding: 14px; border: 1px solid var(--border-primary); }
.ceremony-col h3 { font-size: 14px; margin-bottom: 10px; padding-bottom: 6px;
  border-bottom: 2px solid var(--border-primary); }
.ceremony-col.went-well h3 { color: var(--success); border-color: var(--success); }
.ceremony-col.to-improve h3 { color: var(--warning); border-color: var(--warning); }
.ceremony-col.action-items h3 { color: var(--accent); border-color: var(--accent); }
.ceremony-item { font-size: 13px; color: var(--text-secondary);
  padding: 6px 0; border-bottom: 1px solid var(--border-light); }

/* Budget bars */
.budget-row { display: flex; align-items: center; gap: 12px;
  padding: 8px 0; border-bottom: 1px solid var(--border-light); }
.budget-row .dept-name { width: 120px; font-size: 13px; color: var(--text-primary); }
.budget-row .budget-bar-wrap { flex: 1; }
.budget-row .budget-nums { width: 140px; font-family: var(--font-mono);
  font-size: 12px; color: var(--text-muted); text-align: right; }

/* Sprint goals */
.sprint-goals { list-style: none; padding: 0; margin: 8px 0; }
.sprint-goals li { font-size: 13px; color: var(--text-secondary);
  padding: 4px 0 4px 22px; position: relative; }
.sprint-goals li::before { content: "\\1F3AF"; position: absolute; left: 0; }

/* Standup accordion */
.standup-detail { margin-bottom: 8px; }
.standup-detail summary { cursor: pointer; font-size: 14px; color: var(--text-primary);
  padding: 8px 12px; background: var(--bg-secondary); border-radius: 6px;
  border: 1px solid var(--border-primary); }
.standup-entries { padding: 12px; }
.standup-entry { background: var(--bg-tertiary); border-radius: 6px;
  padding: 10px; margin-bottom: 8px; font-size: 13px; }
.standup-entry .dept { font-weight: 600; color: var(--accent); margin-bottom: 4px; }
.standup-entry .field { color: var(--text-muted); }
.standup-entry .field span { color: var(--text-secondary); }
"""

_DROPDOWN_JS = """\
<script>
document.querySelectorAll('.nav-dropdown-btn').forEach(function(btn){
  btn.addEventListener('click',function(e){
    e.stopPropagation();
    var dd=btn.parentElement;
    var open=dd.classList.toggle('open');
    btn.setAttribute('aria-expanded',open);
  });
});
document.addEventListener('click',function(){
  document.querySelectorAll('.nav-dropdown.open').forEach(function(dd){
    dd.classList.remove('open');
    dd.querySelector('.nav-dropdown-btn').setAttribute('aria-expanded','false');
  });
});
document.querySelectorAll('.nav-dropdown-menu a').forEach(function(a){
  a.addEventListener('click',function(){
    var dd=a.closest('.nav-dropdown');
    if(dd){dd.classList.remove('open');
      dd.querySelector('.nav-dropdown-btn').setAttribute('aria-expanded','false');}
  });
});
</script>
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
    "A-TIER": "badge-green",
    "B-TIER": "badge-blue",
    "C-TIER": "badge-gray",
    "D-TIER": "badge-yellow",
    "F-TIER": "badge-red",
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

# Strategy type labels and descriptions
_STRATEGY_LABELS: dict[str, str] = {
    "ath_mean_reversion": "ATH Mean-Reversion",
    "rsi_oversold": "RSI Oversold",
    "bollinger_lower": "Bollinger Lower Band",
    "ma_dip": "Moving Average Dip",
}

_STRATEGY_DESCRIPTIONS: dict[str, str] = {
    "ath_mean_reversion": (
        "Buy leveraged ETF when its underlying index drops a threshold % "
        "from all-time high, exit at profit target. Captures mean-reversion "
        "after broad market drawdowns."
    ),
    "rsi_oversold": (
        "Buy when 14-day RSI falls below oversold threshold (typically 30), "
        "exit when RSI recovers above overbought level or profit target hit. "
        "Targets short-term momentum reversals."
    ),
    "bollinger_lower": (
        "Buy when price touches or breaks below the lower Bollinger Band "
        "(20-day SMA minus 2 standard deviations), exit at the middle band "
        "or profit target. Identifies statistical extremes in price action."
    ),
    "ma_dip": (
        "Buy when price dips a threshold % below its 50-day moving average, "
        "exit when price recovers to or above the MA. Captures pullbacks "
        "within an established trend."
    ),
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
    "congress": "account_balance",
    "predictions": "casino",
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


def _strategy_badge(strategy_key: str, short_label: str = "") -> str:
    """Return a strategy type badge with tooltip description."""
    label = short_label or _STRATEGY_LABELS.get(strategy_key, strategy_key)
    desc = _STRATEGY_DESCRIPTIONS.get(strategy_key, "")
    title = f' title="{html.escape(desc)}"' if desc else ""
    return f'<span class="badge badge-gray"{title}>{html.escape(label)}</span>'


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
        'family=Inter:wght@300;400;500;600;700&amp;display=swap"'
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
        '<meta name="theme-color" content="#0b0f18">\n'
        f"{desc_tag}"
        f"<title>{html.escape(title)}</title>\n"
        f"{fonts}"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        '<a href="#main-content" class="skip-nav">Skip to main content</a>\n'
        f"{body}\n{_DROPDOWN_JS}\n</body>\n</html>\n"
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

    # 5. Earnings risk
    try:
        from app.sec.earnings import fetch_all_earnings_calendars
        from app.sec.holdings import get_all_unique_holdings as _get_holdings

        _holdings = _get_holdings()
        _calendars = fetch_all_earnings_calendars(_holdings)
        _upcoming = sum(
            1
            for c in _calendars
            if c.days_until_earnings is not None and 0 < c.days_until_earnings <= 14
        )
        _imminent = sum(
            1
            for c in _calendars
            if c.days_until_earnings is not None and 0 < c.days_until_earnings <= 3
        )
        _recent_misses = sum(
            1
            for c in _calendars
            for e in c.recent_events[:2]
            if e.surprise_pct is not None and e.surprise_pct < -0.05
        )
        factors.append(assess_earnings_risk(_upcoming, _imminent, _recent_misses))
    except Exception:
        factors.append(
            FactorResult(
                "earnings_risk",
                FactorAssessment.NEUTRAL,
                "Earnings data unavailable",
            )
        )

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

    # 10. Fundamentals health (from SEC XBRL filings)
    try:
        import os

        from app.sec.fundamentals import classify_sector_health, fetch_all_fundamentals
        from app.sec.holdings import get_all_unique_holdings as _get_all_holdings

        _sec_email = os.environ.get("SEC_EDGAR_EMAIL", "")
        if _sec_email:
            _all_holdings = _get_all_holdings()
            _analyses = fetch_all_fundamentals(_all_holdings, _sec_email)
            _sector_health = classify_sector_health(_analyses)
            factors.append(assess_fundamentals_health(_sector_health))
        else:
            factors.append(
                FactorResult(
                    "fundamentals_health",
                    FactorAssessment.NEUTRAL,
                    "SEC_EDGAR_EMAIL not set",
                )
            )
    except Exception:
        factors.append(
            FactorResult(
                "fundamentals_health",
                FactorAssessment.NEUTRAL,
                "Fundamentals data unavailable",
            )
        )

    # 11. Prediction markets (Polymarket)
    poly = _parse_output(outputs.get("polymarket.summary", ""))
    poly_signal = "NEUTRAL"
    if isinstance(poly, dict):
        poly_signal = str(poly.get("overall_signal", "NEUTRAL"))
    factors.append(assess_prediction_markets(poly_signal))

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
    # Strategy type short labels for table cells
    strategy_short: dict[str, str] = {
        "ath_mean_reversion": "ATH",
        "rsi_oversold": "RSI",
        "bollinger_lower": "Bollinger",
        "ma_dip": "MA Dip",
    }

    rows: list[str] = []
    for p in data[:12]:
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

        # Strategy type badge with tooltip
        stype = str(p.get("strategy_type", "ath_mean_reversion"))
        stype_label = strategy_short.get(stype, stype)

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
            f"<td>{_strategy_badge(stype, stype_label)}</td>"
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
        threshold_label = str(p.get("threshold_label", "drawdown %"))
        strategy_desc = str(p.get("strategy_description", ""))

        detail_parts: list[str] = []
        if strategy_desc:
            detail_parts.append(
                f'<span><span class="label">Strategy:</span> '
                f"{html.escape(strategy_desc)}</span>",
            )
        if isinstance(proposed_threshold, (int, float)):
            entry_str = f"{threshold_label}: {proposed_threshold}"
            if isinstance(current_threshold, (int, float)):
                entry_str += f" (current: {current_threshold})"
            entry_esc = html.escape(entry_str)
            detail_parts.append(
                f'<span><span class="label">Entry:</span> {entry_esc}</span>',
            )
        if isinstance(proposed_target, (int, float)):
            exit_str = f"+{proposed_target:.0%} profit target"
            if isinstance(current_target, (int, float)):
                exit_str += f" (current: +{current_target:.0%})"
            exit_esc = html.escape(exit_str)
            detail_parts.append(
                f'<span><span class="label">Exit:</span> {exit_esc}</span>',
            )
        if avg_hold:
            hold_esc = html.escape(avg_hold)
            detail_parts.append(
                f'<span><span class="label">Avg Hold:</span> {hold_esc}</span>',
            )
        if detail_parts:
            rows.append(
                '<tr><td colspan="9"><div class="strategy-entry-exit">'
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
        "of historical data. Strategy optimizer tests <strong>4 strategy "
        "types</strong> (ATH Mean-Reversion, RSI Oversold, Bollinger Lower, "
        "MA Dip) with multiple parameter combinations per ETF, "
        "ranked by Sharpe ratio.</p>",
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
        '<th scope="col">ETF</th><th scope="col">Strategy</th>'
        '<th scope="col">Proposal</th>'
        '<th scope="col" class="num">Sharpe</th>'
        '<th scope="col" class="num">Win Rate</th>'
        '<th scope="col" class="num">Return</th>'
        '<th scope="col" class="num">Trades</th>'
        '<th scope="col" class="num">Max DD</th>'
        '<th scope="col" class="num">Avg Hold</th>'
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


# --- Sector fundamentals section ---


def _fund_pct(val: float | None) -> str:
    """Format a fundamentals percentage, or dash if None."""
    if val is None:
        return '<span class="text-muted">&mdash;</span>'
    return f"{val:.0%}"


def _fund_ratio(val: float | None) -> str:
    """Format a fundamentals ratio, or dash if None."""
    if val is None:
        return '<span class="text-muted">&mdash;</span>'
    return f"{val:.1f}"


def _fund_trend(trend: str) -> str:
    """Return a colored arrow for margin trends."""
    if trend == "IMPROVING":
        return '<span class="pct-up">&#x25B2;</span>'
    if trend == "DECLINING":
        return '<span class="pct-down">&#x25BC;</span>'
    return '<span class="text-muted">&#x2014;</span>'


def _section_fundamentals(outputs: dict[str, str]) -> str:
    """Render sector fundamentals from SEC XBRL filings."""
    import os

    from app.sec.fundamentals import (
        classify_sector_health,
        fetch_all_fundamentals,
    )
    from app.sec.holdings import INDEX_HOLDINGS

    sec_email = os.environ.get("SEC_EDGAR_EMAIL", "")
    if not sec_email:
        return ""

    # Map index -> leveraged ETF for display context
    index_etf: dict[str, str] = {
        "QQQ": "TQQQ/TECL",
        "SOXX": "SOXL",
        "XLF": "FAS",
        "XLE": "UCO",
        "XBI": "LABU",
        "SPY": "UPRO",
        "IWM": "TNA",
        "XLK": "TECL",
    }

    sector_parts: list[str] = []

    for index, holdings in INDEX_HOLDINGS.items():
        if not holdings:
            continue

        try:
            analyses = fetch_all_fundamentals(holdings, sec_email)
        except Exception:  # noqa: S112
            continue

        if not analyses:
            continue

        sector_health = classify_sector_health(analyses)
        etf_label = index_etf.get(index, "")
        etf_badge = ""
        if etf_label:
            etf_badge = (
                f' <span class="badge badge-blue">'
                f"{html.escape(etf_label)}</span>"
            )

        health_badge = _badge(sector_health)

        rows: list[str] = []
        for a in analyses:
            ticker = html.escape(a.ticker)
            h_badge = _badge(a.health)
            rev_growth = _fmt_growth(a.revenue_growth_yoy)
            gm = _fund_pct(a.gross_margin)
            om = _fund_pct(a.operating_margin)
            de = _fund_ratio(a.debt_to_equity)
            fcf = _fund_ratio(a.fcf_to_net_income)
            gm_arrow = _fund_trend(a.gross_margin_trend)
            om_arrow = _fund_trend(a.operating_margin_trend)

            rows.append(
                f"<tr>"
                f"<td><strong>{ticker}</strong></td>"
                f'<td class="num">{rev_growth}</td>'
                f'<td class="num">{gm} {gm_arrow}</td>'
                f'<td class="num">{om} {om_arrow}</td>'
                f'<td class="num">{de}</td>'
                f'<td class="num">{fcf}</td>'
                f"<td>{h_badge}</td>"
                f"</tr>",
            )

        table = (
            '<table class="mt-8">\n'
            "<thead><tr>"
            '<th scope="col">Ticker</th>'
            '<th scope="col" class="num">Rev YoY</th>'
            '<th scope="col" class="num">Gross M</th>'
            '<th scope="col" class="num">Op M</th>'
            '<th scope="col" class="num">D/E</th>'
            '<th scope="col" class="num">FCF/NI</th>'
            '<th scope="col">Health</th>'
            "</tr></thead>\n<tbody>\n"
            + "\n".join(rows)
            + "\n</tbody></table>\n"
        )

        sector_parts.append(
            f'<div style="margin-bottom:20px">'
            f"<p><strong>{html.escape(index)}</strong>"
            f" {health_badge}{etf_badge}</p>"
            f"{table}"
            f"</div>",
        )

    if not sector_parts:
        return ""

    return (
        '<section id="fundamentals">\n'
        f"<h2>{_section_icon('monitoring')}"
        f"Sector Fundamentals</h2>\n"
        '<div class="card">\n'
        '<p class="kicker">Financial Health from SEC Filings</p>'
        "<p>Income statement, balance sheet, and cash flow "
        "metrics from actual 10-K/10-Q XBRL filings. "
        "Arrows show YoY margin trends.</p>\n"
        + "\n".join(sector_parts)
        + "\n</div>\n"
        "</section>\n"
    )


def _fmt_growth(val: float | None) -> str:
    """Format a growth percentage with color."""
    if val is None:
        return '<span class="text-muted">&mdash;</span>'
    cls = "pct-up" if val >= 0 else "pct-down"
    return f'<span class="{cls}">{val:+.0%}</span>'


# --- Congress trading section ---


def _section_congress(outputs: dict[str, str]) -> str:
    """Render Congressional stock trading activity section."""
    data = _parse_output(outputs.get("congress.summary", ""))
    if not isinstance(data, dict):
        return ""

    parts: list[str] = []

    # Overall sentiment + trade counts
    sentiment = str(data.get("overall_sentiment", "NEUTRAL"))
    trades_30d = data.get("trades_last_30d", 0)
    trades_90d = data.get("total_trades_90d", 0)
    net_usd = data.get("net_buying_usd", 0)

    net_str = ""
    if isinstance(net_usd, (int, float)):
        sign = "+" if net_usd >= 0 else ""
        net_str = f" &mdash; Net: {sign}${abs(net_usd):,.0f}"

    parts.append(
        f"<p>Overall: {_badge(sentiment)}{net_str}</p>"
        f'<p class="text-muted" style="font-size:12px">'
        f"{trades_30d} trades (30d) &bull; {trades_90d} trades (90d)</p>"
    )

    # Sector breakdown table
    sectors = data.get("sectors", [])
    if isinstance(sectors, list) and sectors:
        rows: list[str] = []
        for sec in sectors:
            if not isinstance(sec, dict):
                continue
            name = html.escape(str(sec.get("sector", "")))
            lev = html.escape(str(sec.get("leveraged", "")))
            sec_sent = str(sec.get("sentiment", "NEUTRAL"))
            sec_net = sec.get("net_usd", 0)
            sec_trades = sec.get("trades", 0)
            if isinstance(sec_net, (int, float)) and sec_net > 0:
                net_cls = "pct-up"
            elif isinstance(sec_net, (int, float)) and sec_net < 0:
                net_cls = "pct-down"
            else:
                net_cls = ""
            net_display = ""
            if isinstance(sec_net, (int, float)):
                sign = "+" if sec_net >= 0 else ""
                net_display = f"{sign}${abs(sec_net):,.0f}"
            # Top tickers traded in this sector
            tickers_html = ""
            top_tickers = sec.get("top_tickers", [])
            if isinstance(top_tickers, list) and top_tickers:
                chips: list[str] = []
                for tk in top_tickers[:5]:
                    if not isinstance(tk, dict):
                        continue
                    t = html.escape(str(tk.get("ticker", "")))
                    tc = tk.get("trades", 0)
                    tn = tk.get("net_usd", 0)
                    cls = (
                        "pct-up"
                        if isinstance(tn, (int, float)) and tn > 0
                        else (
                            "pct-down"
                            if isinstance(tn, (int, float)) and tn < 0
                            else ""
                        )
                    )
                    chips.append(
                        f'<span class="sector-badge {cls}">{t} ({tc})</span>',
                    )
                if chips:
                    tickers_html = (
                        '<tr><td colspan="5" style='
                        '"padding:4px 14px 10px">'
                        f"{''.join(chips)}</td></tr>"
                    )

            rows.append(
                f"<tr><td>{name}</td>"
                f"<td>{lev}</td>"
                f"<td>{_badge(sec_sent)}</td>"
                f'<td class="num {net_cls}">{net_display}</td>'
                f'<td class="num">{sec_trades}</td></tr>'
                f"{tickers_html}"
            )
        if rows:
            parts.append(
                '<div style="overflow-x:auto; margin-top:12px">'
                "<table>"
                "<thead><tr>"
                "<th>Sector</th><th>ETF</th><th>Sentiment</th>"
                '<th class="num">Net Flow</th><th class="num">Trades</th>'
                "</tr></thead>"
                f"<tbody>{''.join(rows)}</tbody>"
                "</table></div>"
            )

    # Top members
    members = data.get("top_members", [])
    if isinstance(members, list) and members:
        parts.append('<div class="congress-grid">')
        for mem in members[:8]:
            if not isinstance(mem, dict):
                continue
            name = html.escape(str(mem.get("name", "")))
            tier = str(mem.get("tier", "C"))
            win_rate = mem.get("win_rate", 0)
            m_trades = mem.get("trades", 0)
            chamber = html.escape(str(mem.get("chamber", "")))
            t = tier.lower()
            tier_cls = f"tier-{t}" if t in "abcdf" else "tier-c"
            wr_str = f"{win_rate:.0%}" if isinstance(win_rate, float) else str(win_rate)
            parts.append(
                f'<div class="congress-member {tier_cls}">'
                f'<div class="congress-member-name">{name}</div>'
                f'<div class="congress-member-meta">'
                f"{_badge(tier + '-TIER')} {chamber} &bull; "
                f"Win: {wr_str} &bull; {m_trades} trades"
                "</div></div>"
            )
        parts.append("</div>")

    if not parts:
        return ""
    return (
        '<section id="congress">\n'
        f"<h2>{_section_icon('congress')}Congressional Trading</h2>\n"
        '<div class="card">\n' + "\n".join(parts) + "\n</div>\n"
        "</section>\n"
    )


# --- Prediction markets section ---


def _section_polymarket(outputs: dict[str, str]) -> str:
    """Render Polymarket prediction markets section."""
    data = _parse_output(outputs.get("polymarket.summary", ""))
    if not isinstance(data, dict):
        return ""

    parts: list[str] = []

    # Overall signal + counts
    overall = str(data.get("overall_signal", "NEUTRAL"))
    total = data.get("total_markets", 0)
    relevant = data.get("relevant_markets", 0)
    fav = data.get("favorable_count", 0)
    unfav = data.get("unfavorable_count", 0)

    parts.append(
        f"<p>Overall: {_badge(overall)}</p>"
        f'<p class="text-muted" style="font-size:12px">'
        f"{total} markets tracked &bull; {relevant} with signals "
        f"&bull; {fav} favorable &bull; {unfav} unfavorable</p>"
    )

    # Category breakdown
    cats = data.get("markets_by_category", {})
    if isinstance(cats, dict) and cats:
        cat_rows: list[str] = []
        for cat, count in sorted(cats.items()):
            label = cat.replace("_", " ").title()
            cat_rows.append(f"<tr><td>{html.escape(label)}</td>"
                            f'<td class="num">{count}</td></tr>')
        if cat_rows:
            parts.append(
                '<div style="overflow-x:auto; margin-top:12px">'
                "<table><thead><tr>"
                "<th>Category</th>"
                '<th class="num">Markets</th>'
                "</tr></thead>"
                f"<tbody>{''.join(cat_rows)}</tbody>"
                "</table></div>"
            )

    # Sector signals
    sectors = data.get("affected_sectors", {})
    if isinstance(sectors, dict) and sectors:
        sec_rows: list[str] = []
        for sector, sig in sorted(sectors.items()):
            label = sector.replace("_", " ").title()
            sec_rows.append(f"<tr><td>{html.escape(label)}</td>"
                            f"<td>{_badge(str(sig))}</td></tr>")
        if sec_rows:
            parts.append(
                '<div style="overflow-x:auto; margin-top:12px">'
                "<table><thead><tr>"
                "<th>Sector</th><th>Signal</th>"
                "</tr></thead>"
                f"<tbody>{''.join(sec_rows)}</tbody>"
                "</table></div>"
            )

    # Top markets
    top = data.get("top_markets", [])
    if isinstance(top, list) and top:
        mkt_rows: list[str] = []
        for m in top[:10]:
            if not isinstance(m, dict):
                continue
            q = html.escape(str(m.get("question", ""))[:80])
            cat = html.escape(
                str(m.get("category", "")).replace("_", " ").title()
            )
            sig = str(m.get("signal", "NEUTRAL"))
            prob = m.get("probability", 0)
            prob_pct = f"{prob:.0%}" if isinstance(prob, (int, float)) else str(prob)
            # Probability bar
            bar_w = int(float(prob) * 100) if isinstance(prob, (int, float)) else 50
            bar_color = (
                "var(--accent-green)" if sig == "FAVORABLE"
                else "var(--accent-red)" if sig == "UNFAVORABLE"
                else "var(--text-muted)"
            )
            bar_html = (
                f'<div style="background:var(--bg-secondary);border-radius:4px;'
                f'height:8px;width:80px;display:inline-block;vertical-align:middle">'
                f'<div style="background:{bar_color};height:100%;'
                f'width:{bar_w}%;border-radius:4px"></div></div>'
                f' <span style="font-size:11px">{prob_pct}</span>'
            )
            mkt_rows.append(
                f"<tr><td>{q}</td><td>{cat}</td>"
                f"<td>{_badge(sig)}</td><td>{bar_html}</td></tr>"
            )
        if mkt_rows:
            parts.append(
                '<div style="overflow-x:auto; margin-top:12px">'
                "<table><thead><tr>"
                "<th>Market</th><th>Category</th>"
                "<th>Signal</th><th>Probability</th>"
                "</tr></thead>"
                f"<tbody>{''.join(mkt_rows)}</tbody>"
                "</table></div>"
            )

    if not parts:
        return ""
    return (
        '<section id="predictions">\n'
        f"<h2>{_section_icon('predictions')}Prediction Markets</h2>\n"
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

    # Gather unique strategies, tickers tested
    strategies: set[str] = set()
    tickers: list[str] = []
    for p in data:
        if not isinstance(p, dict):
            continue
        st = str(p.get("strategy_type", ""))
        if st:
            strategies.add(st)
        tk = str(p.get("leveraged_ticker", ""))
        if tk and tk not in tickers:
            tickers.append(tk)

    if not tickers:
        return ""

    parts: list[str] = [
        '<p class="kicker">Strategy Research</p>',
        "<p>The multi-strategy optimizer explored "
        f"<strong>{len(tickers)} ETF(s)</strong> across "
        f"<strong>{len(strategies) or 4} strategy types</strong> "
        "with multiple parameter combinations each. "
        "Results are ranked by risk-adjusted returns (Sharpe ratio).</p>",
    ]

    if strategies:
        strat_items: list[str] = []
        for s in sorted(strategies):
            label = _STRATEGY_LABELS.get(s, s)
            desc = _STRATEGY_DESCRIPTIONS.get(s, "")
            escaped_label = html.escape(label)
            escaped_desc = html.escape(desc)
            strat_items.append(
                f'<div style="padding:8px 0;'
                f'border-bottom:1px solid var(--border-light)">'
                f'<span class="badge badge-gray">{escaped_label}</span>'
                f' <span style="font-size:13px;color:var(--text-secondary)">'
                f"&mdash; {escaped_desc}</span></div>",
            )
        parts.append(
            '<div class="mt-12">' + "\n".join(strat_items) + "</div>",
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


def _section_strategy_summary_card(
    outputs: dict[str, str],
    date: str,
) -> str:
    """Render a compact strategy summary card linking to the Strategies page."""
    data = _parse_output(outputs.get("strategy.proposals", ""))
    if not isinstance(data, list) or not data:
        return ""
    n_proposals = len(data)
    tickers: set[str] = set()
    for p in data:
        if isinstance(p, dict):
            tk = str(p.get("leveraged_ticker", ""))
            if tk:
                tickers.add(tk)
    detail = f"{n_proposals} proposals across {len(tickers)} ETFs"
    href = html.escape(f"strategies-{date}.html")
    return (
        f'<a class="summary-link-card" href="{href}">\n'
        '<div class="card-title">Strategy Proposals</div>\n'
        f'<div class="card-detail">{html.escape(detail)}</div>\n'
        '<div class="card-cta">View details &rarr;</div>\n'
        "</a>\n"
    )


def _section_research_summary_card(
    outputs: dict[str, str],
    date: str,
) -> str:
    """Render a compact research summary card linking to the Research page."""
    research_data = _parse_output(outputs.get("research.summary", ""))
    detail = "Research pipeline and documents"
    if isinstance(research_data, dict):
        docs = research_data.get("documents", [])
        if isinstance(docs, list) and docs:
            detail = f"{len(docs)} research documents available"
    href = html.escape(f"research-{date}.html")
    return (
        f'<a class="summary-link-card" href="{href}">\n'
        '<div class="card-title">Strategy Research</div>\n'
        f'<div class="card-detail">{html.escape(detail)}</div>\n'
        '<div class="card-cta">View details &rarr;</div>\n'
        "</a>\n"
    )


_NAV_ITEMS: list[dict[str, object]] = [
    {"key": "dashboard", "label": "Dashboard", "prefix": ""},
    {
        "key": "trading",
        "label": "Trading",
        "dropdown": True,
        "children": [
            {"key": "forecasts", "label": "Forecasts", "prefix": "forecasts-"},
            {"key": "strategies", "label": "Strategies", "prefix": "strategies-"},
            {"key": "trade-log", "label": "Trade Log", "prefix": "trade-log-"},
        ],
    },
    {"key": "financials", "label": "Financials", "prefix": "financials-"},
    {
        "key": "operations",
        "label": "Operations",
        "dropdown": True,
        "children": [
            {
                "key": "sprint-board",
                "label": "Sprint Board",
                "prefix": "sprint-board-",
            },
            {"key": "roadmap", "label": "Roadmap", "prefix": "roadmap-"},
            {
                "key": "system-health",
                "label": "System Health",
                "prefix": "system-health-",
            },
        ],
    },
    {"key": "research", "label": "Research", "prefix": "research-"},
    {"key": "about", "label": "About", "prefix": "about-"},
]


def _page_header_bar(
    date: str,
    active_page: str,
    report_dates: list[str] | None = None,
    *,
    page_prefix: str = "",
) -> str:
    """Render a unified navy top bar with title, navigation, and date picker.

    Args:
        date: Report date string (YYYY-MM-DD) for building page hrefs.
        active_page: Key identifying the current page (e.g. "dashboard").
        report_dates: Available report dates (newest first) for the picker.
        page_prefix: File prefix for the current page (for date picker nav).
    """
    nav_html_parts: list[str] = []
    for item in _NAV_ITEMS:
        if item.get("dropdown"):
            children = item.get("children", [])
            assert isinstance(children, list)
            # Check if any child is the active page
            child_active = any(
                c.get("key") == active_page  # type: ignore[union-attr]
                for c in children
            )
            btn_cls = ' nav-active' if child_active else ""
            child_links = []
            for child in children:
                assert isinstance(child, dict)
                href = f"{child['prefix']}{date}.html"
                a_cls = ' class="nav-active"' if child["key"] == active_page else ""
                child_links.append(
                    f'<a href="{html.escape(href)}"{a_cls}>'
                    f'{child["label"]}</a>',
                )
            menu_html = "".join(child_links)
            nav_html_parts.append(
                f'<div class="nav-dropdown">'
                f'<button class="nav-dropdown-btn{btn_cls}" '
                f'aria-haspopup="true" aria-expanded="false">'
                f'{item["label"]}</button>'
                f'<div class="nav-dropdown-menu">{menu_html}</div>'
                f"</div>",
            )
        else:
            href = f"{item['prefix']}{date}.html"
            cls = ' class="nav-active"' if item["key"] == active_page else ""
            nav_html_parts.append(
                f'<a href="{html.escape(href)}"{cls}>{item["label"]}</a>',
            )

    parts = "".join(nav_html_parts)

    # Section anchors as dropdown on dashboard page
    if active_page == "dashboard":
        section_links = [
            ("#signals", "Signals"),
            ("#sentiment", "Sentiment"),
            ("#market", "Market"),
            ("#risks", "Risks"),
            ("#geopolitical", "Geopolitical"),
            ("#congress", "Congress"),
            ("#predictions", "Predictions"),
        ]
        section_items = "".join(
            f'<a href="{href}">{label}</a>' for href, label in section_links
        )
        parts += (
            '<span class="nav-divider"></span>'
            '<div class="nav-dropdown">'
            '<button class="nav-dropdown-btn" '
            'aria-haspopup="true" aria-expanded="false">'
            "Sections</button>"
            f'<div class="nav-dropdown-menu">{section_items}</div>'
            "</div>"
        )

    # Date picker dropdown — navigates to same page type for selected date
    date_picker = ""
    if report_dates and len(report_dates) > 1:
        options = []
        for d in report_dates:
            escaped = html.escape(d)
            selected = " selected" if d == date else ""
            options.append(
                f'<option value="{escaped}"{selected}>{escaped}</option>',
            )
        opts_html = "".join(options)
        pfx_escaped = html.escape(page_prefix)
        date_picker = (
            '<select class="nav-date-picker" '
            'aria-label="Select report date" '
            f"onchange=\"window.location.href='{pfx_escaped}'"
            "+this.value+'.html'\">"
            f"{opts_html}</select>\n"
        )

    return (
        '<div class="top-bar">\n'
        '<h1><img src="../logo.png" alt="Be Him" class="top-bar-logo">'
        "Swing Trading Report</h1>\n"
        f"{date_picker}"
        f'<nav class="nav-menu" aria-label="Report navigation">{parts}</nav>\n'
        "</div>\n"
    )


def build_html_report(
    run: SchedulerRun,
    *,
    date: str = "",
    report_dates: list[str] | None = None,
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
    market_risks = _section_market_risks(outputs)
    geopolitical = _section_geopolitical(outputs)
    fundamentals = _section_fundamentals(outputs)
    congress = _section_congress(outputs)
    predictions = _section_polymarket(outputs)
    strategy_card = _section_strategy_summary_card(outputs, report_date)
    research_card = _section_research_summary_card(outputs, report_date)

    top_bar = _page_header_bar(
        report_date, "dashboard", report_dates, page_prefix="",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; {html.escape(report_time)}</span>\n"
        '<div class="header-status">'
        f'<span class="ok">{run.succeeded}</span>/{run.total_modules} OK'
        f' &bull; <span class="fail">{run.failed}</span> failed'
        "</div>\n</header>\n"
    )

    # Build widget grid — all 4 sections as equal widgets in 2-col grid
    def _widget(title: str, content: str) -> str:
        return (
            '<div class="rpt-widget">\n'
            f'<div class="rpt-widget-title">{html.escape(title)}</div>\n'
            f"{content}\n"
            "</div>\n"
        )

    grid_widgets: list[str] = []
    if signal_cards:
        grid_widgets.append(_widget("Entry Signals & Positions", signal_cards))
    if kpi:
        grid_widgets.append(_widget("Key Indicators", kpi))
    if conditions:
        grid_widgets.append(_widget("Market Overview", conditions))
    events_parts = [p for p in [sentiment, geopolitical] if p]
    if events_parts:
        grid_widgets.append(
            _widget("Market-Moving Events", "\n".join(events_parts)),
        )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "not financial advice.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        '<div class="rpt-compact">\n',
        exec_summary,
        '<div class="rpt-layout">\n',
        *grid_widgets,
        "</div>\n",
        market_risks,
        fundamentals,
        congress,
        predictions,
        strategy_card,
        research_card,
        "</div>\n",
        "</main>\n",
        footer,
    ]
    return _html_page(
        title=f"Dashboard {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"Daily leveraged ETF swing trading dashboard for {report_date}",
    )


_ETF_WATCHLIST: list[tuple[str, str]] = [
    ("TQQQ", "Tech 3x"),
    ("TECL", "Tech 3x"),
    ("SOXL", "Semi 3x"),
    ("FAS", "Fin 3x"),
    ("UCO", "Oil 2x"),
    ("LABU", "Bio 3x"),
    ("UPRO", "S&P 3x"),
    ("TNA", "SmCap 3x"),
]

_SUB_PAGES: list[tuple[str, str, str]] = [
    # (prefix, label, icon -- used as tab text)
    ("", "Dashboard", "dashboard"),
    ("forecasts-", "Forecasts", "fcst"),
    ("strategies-", "Strategies", "strat"),
    ("trade-log-", "Trade Log", "trades"),
    ("financials-", "Financials", "fin"),
    ("sprint-board-", "Sprint Board", "sprint"),
    ("roadmap-", "Roadmap", "roadmap"),
    ("system-health-", "System Health", "health"),
    ("research-", "Research", "research"),
    ("about-", "About", "about"),
]


def build_index_html(
    report_dates: list[str],
    *,
    sub_pages: dict[str, list[str]] | None = None,
) -> str:
    """Build the index.html landing page — compact Yahoo Finance-style layout.

    *sub_pages* maps each date to a list of available prefixes
    (e.g. ``{"2026-02-13": ["", "trade-logs-", "forecasts-"]}``)
    so we can link to only the pages that actually exist.
    If not provided, only the main report link is shown.
    """
    sub_pages = sub_pages or {}

    # --- ticker bar ---
    ticker_cells: list[str] = []
    for sym, sector in _ETF_WATCHLIST:
        ticker_cells.append(
            f'<div class="idx-ticker">'
            f'<span class="tk-sym">{sym}</span>'
            f'<span class="tk-sector">{sector}</span></div>',
        )
    ticker_bar = '<div class="idx-ticker-bar">\n' + "\n".join(ticker_cells) + "\n</div>"

    # --- helper: build tab links for a date ---
    def _tabs(d: str, prefix_path: str = "reports/") -> str:
        available = sub_pages.get(d, [""])
        parts: list[str] = []
        for pfx, label, _icon in _SUB_PAGES:
            if pfx in available:
                href = f"{prefix_path}{pfx}{html.escape(d)}.html"
                parts.append(f'<a href="{href}" class="idx-tab">{label}</a>')
        if not parts:
            return ""
        return '<div class="idx-featured-tabs">' + "".join(parts) + "</div>"

    # --- main column: featured latest + older reports ---
    featured_html = ""
    older_rows: list[str] = []

    if not report_dates:
        featured_html = (
            '<div class="idx-featured">\n'
            '<div class="idx-featured-kicker">No Reports Yet</div>\n'
            "<h2>0 report(s) available</h2>\n"
            '<div class="idx-featured-meta">'
            "Run a pre-market or post-market analysis to generate your first report."
            "</div>\n</div>\n"
        )
    elif report_dates:
        latest = report_dates[0]
        escaped = html.escape(latest)
        featured_html = (
            '<div class="idx-featured">\n'
            '<div class="idx-featured-kicker">Latest Report</div>\n'
            f'<h2><a href="reports/{escaped}.html">'
            f"Market Report &mdash; {escaped}</a></h2>\n"
            f'<div class="idx-featured-meta">{escaped} '
            f"&middot; {len(report_dates)} report(s) available</div>\n"
            f"{_tabs(latest)}\n"
            "</div>\n"
        )

        for d in report_dates[1:]:
            ed = html.escape(d)
            page_links: list[str] = []
            available = sub_pages.get(d, [""])
            for pfx, label, _icon in _SUB_PAGES:
                if pfx in available:
                    href = f"reports/{pfx}{ed}.html"
                    page_links.append(
                        f'<a href="{href}" class="idx-page-link">{label}</a>',
                    )
            pages_html = (
                '<div class="idx-report-pages">' + "".join(page_links) + "</div>"
                if page_links
                else ""
            )
            older_rows.append(
                f'<div class="idx-report-row">'
                f'<span class="idx-report-date">'
                f'<a href="reports/{ed}.html">{ed}</a></span>'
                f"{pages_html}</div>",
            )

    older_html = ""
    if older_rows:
        older_html = (
            '<div class="idx-section-head">Previous Reports</div>\n'
            + "\n".join(older_rows)
        )

    main_col = f'<div class="idx-main">\n{featured_html}{older_html}\n</div>'

    # --- sidebar: archive quick links + ETF watchlist ---
    archive_items: list[str] = []
    for i, d in enumerate(report_dates):
        ed = html.escape(d)
        badge = ' <span class="badge-latest">LATEST</span>' if i == 0 else ""
        archive_items.append(
            f'<div class="idx-archive-item">'
            f'<a href="reports/{ed}.html">{ed}</a>{badge}</div>',
        )
    archive_section = (
        '<div class="idx-sb-section">\n'
        '<div class="idx-sb-title">Report Archive</div>\n'
        + "\n".join(archive_items)
        + "\n</div>"
    )

    etf_rows: list[str] = []
    for sym, sector in _ETF_WATCHLIST:
        etf_rows.append(
            f'<div class="idx-etf-row">'
            f'<span class="idx-etf-sym">{sym}</span>'
            f'<span class="idx-etf-name">{sector}</span></div>',
        )
    etf_section = (
        '<div class="idx-sb-section">\n'
        '<div class="idx-sb-title">ETF Watchlist</div>\n'
        + "\n".join(etf_rows)
        + "\n</div>"
    )

    sidebar = f'<div class="idx-sidebar">\n{archive_section}\n{etf_section}\n</div>'

    body = (
        '<div class="top-bar">\n'
        '<h1><img src="logo.png" alt="Be Him" class="top-bar-logo">'
        "Swing Trading Report</h1>\n"
        "</div>\n"
        f"{ticker_bar}\n"
        f'<main id="main-content">\n'
        f'<div class="idx-layout">\n{main_col}\n{sidebar}\n</div>\n'
        f"</main>\n"
        '<footer class="footer">\n'
        '<span>Powered by <a href="https://github.com/bikoman57/claude">'
        "fin-agents</a></span>\n</footer>"
    )
    return _html_page(
        title="Trading Reports",
        body=body,
        description="Leveraged ETF swing trading dashboard reports",
    )


# --- Market-Moving Events Watchlist ---

_RISK_CONTEXT: dict[str, dict[str, str | list[str]]] = {
    "TRADE_WAR": {
        "label": "Trade Wars & Tariff Escalation",
        "why": (
            "Tariffs and trade restrictions directly impact tech supply chains, "
            "semiconductor exports, and manufacturing costs."
        ),
        "affected_etfs": ["TQQQ", "SOXL", "TECL"],
        "market_impact": (
            "Bearish for tech/semis; potential rotation to "
            "financials and domestic-focused sectors."
        ),
    },
    "MILITARY": {
        "label": "Military Conflicts & Defense",
        "why": (
            "Military escalation drives oil prices higher and creates "
            "broad risk-off sentiment. Defense sector benefits."
        ),
        "affected_etfs": ["UCO", "TQQQ", "UPRO"],
        "market_impact": (
            "Oil spikes, flight to safety (bonds, gold), tech selloff on risk aversion."
        ),
    },
    "SANCTIONS": {
        "label": "Economic Sanctions",
        "why": (
            "Sanctions disrupt energy supply, banking channels, "
            "and cross-border trade flows."
        ),
        "affected_etfs": ["UCO", "FAS"],
        "market_impact": (
            "Energy volatility, banking sector stress, commodity price dislocations."
        ),
    },
    "ECON_TARIFF": {
        "label": "Tariff Policy Changes",
        "why": (
            "Tariff announcements create immediate supply chain "
            "repricing across affected sectors."
        ),
        "affected_etfs": ["SOXL", "TECL", "TQQQ"],
        "market_impact": (
            "Semiconductor and tech hardware most exposed; "
            "consumer prices and margins compressed."
        ),
    },
    "ELECTION": {
        "label": "Major Elections & Political Shifts",
        "why": (
            "Elections introduce policy uncertainty affecting "
            "regulation, taxation, and trade agreements."
        ),
        "affected_etfs": ["UPRO", "FAS", "TNA"],
        "market_impact": (
            "Broad market volatility around election dates; "
            "sector rotation based on expected policy winners."
        ),
    },
    "TERRITORY": {
        "label": "Territorial Disputes & Sovereignty",
        "why": (
            "Territorial conflicts (e.g., Taiwan, South China Sea) "
            "threaten critical semiconductor supply chains."
        ),
        "affected_etfs": ["SOXL", "TQQQ", "TECL"],
        "market_impact": (
            "Extreme downside risk for semis if Taiwan escalates; "
            "broad tech exposure via supply chain dependencies."
        ),
    },
}


def _section_market_risks(outputs: dict[str, str]) -> str:
    """Render Market-Moving Events Watchlist with risk context."""
    geo = _parse_output(outputs.get("geopolitical.summary", ""))
    if not isinstance(geo, dict):
        return ""

    cats = geo.get("events_by_category", {})
    if not isinstance(cats, dict) or not cats:
        return ""

    parts: list[str] = [
        '<p class="kicker">Events Watchlist</p>',
        "<p>Ongoing world events being monitored for potential "
        "market impact. Each theme is tracked via GDELT global "
        "event data and classified by affected sectors.</p>",
    ]

    for cat_key, count in sorted(
        cats.items(),
        key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
        reverse=True,
    ):
        ctx = _RISK_CONTEXT.get(str(cat_key))
        if ctx is None:
            continue

        label = html.escape(str(ctx["label"]))
        why = html.escape(str(ctx["why"]))
        impact = html.escape(str(ctx["market_impact"]))
        etfs = ctx.get("affected_etfs", [])
        etf_badges = ""
        if isinstance(etfs, list):
            etf_badges = " ".join(
                f'<span class="badge badge-blue">{html.escape(str(e))}</span>'
                for e in etfs
            )

        event_count = int(count) if isinstance(count, (int, float)) else 0
        count_badge = (
            _badge("HIGH")
            if event_count > 20
            else (_badge("MEDIUM") if event_count > 5 else _badge("LOW"))
        )

        parts.append(
            '<div style="padding:12px 0;'
            'border-bottom:1px solid var(--border-light)">'
            f"<p><strong>{label}</strong> "
            f'{count_badge} <span class="text-muted">'
            f"({event_count} events)</span></p>"
            f'<p style="font-size:13px;color:var(--text-secondary)'
            f';margin-top:4px">{why}</p>'
            f'<p style="font-size:12px;color:var(--text-muted)'
            f';margin-top:4px">'
            f'<span class="label">Impact:</span> {impact}</p>'
            f'<div style="margin-top:6px">{etf_badges}</div>'
            "</div>",
        )

    if len(parts) <= 2:
        return ""

    return (
        '<section id="risks">\n'
        f"<h2>{_section_icon('globe')}Market-Moving Events</h2>\n"
        '<div class="card">\n' + "\n".join(parts) + "\n</div>\n"
        "</section>\n"
    )


# --- Trade Logs Page ---

_CHART_COLORS: list[str] = [
    "#2563eb",  # accent blue
    "#0a7c42",  # green
    "#1565c0",  # blue
    "#b86e00",  # amber
    "#6a1b9a",  # purple
    "#00838f",  # teal
    "#c62828",  # red
    "#37474f",  # dark gray
]


def build_trade_log_html(
    outputs: dict[str, str],
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build trade log page with Chart.js equity curve and trade history."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    data = _parse_output(outputs.get("strategy.backtest-all", ""))
    if not isinstance(data, list) or not data:
        return ""

    # Build Chart.js datasets
    chart_datasets: list[str] = []
    all_rows: list[str] = []
    summary_rows: list[str] = []

    strat_short: dict[str, str] = {
        "ath_mean_reversion": "ATH",
        "rsi_oversold": "RSI",
        "bollinger_lower": "Bollinger",
        "ma_dip": "MA Dip",
    }

    for idx, etf in enumerate(data):
        if not isinstance(etf, dict):
            continue

        ticker = str(etf.get("leveraged_ticker", "?"))
        underlying = str(etf.get("underlying_ticker", "?"))
        stype = str(etf.get("strategy_type", "ath_mean_reversion"))
        stype_label = strat_short.get(stype, stype)
        equity = etf.get("equity_curve", [])
        trades = etf.get("trades", [])
        total_ret = etf.get("total_return", 0)
        sharpe = etf.get("sharpe_ratio")
        win_rate = etf.get("win_rate")
        max_dd = etf.get("max_drawdown", 0)
        trade_count = etf.get("trade_count", 0)
        threshold = etf.get("entry_threshold", 0)
        profit_target = etf.get("profit_target", 0)

        color = _CHART_COLORS[idx % len(_CHART_COLORS)]
        chart_label = f"{ticker} ({stype_label})"

        if isinstance(equity, list) and equity:
            equity_json = json.dumps(equity)
            labels_json = json.dumps(list(range(len(equity))))
            chart_datasets.append(
                "{"
                f'label:"{html.escape(chart_label)}",'
                f"data:{equity_json},"
                f'borderColor:"{color}",'
                f'backgroundColor:"{color}22",'
                "borderWidth:2,"
                "pointRadius:3,"
                "pointHoverRadius:5,"
                "tension:0.1,"
                "fill:false"
                "}",
            )

        # Summary row
        ret_cls = _pct_class(total_ret)
        sharpe_str = f"{sharpe:.3f}" if isinstance(sharpe, (int, float)) else "N/A"
        wr_str = _fmt_pct(win_rate) if isinstance(win_rate, (int, float)) else "N/A"
        ret_str = _fmt_pct(total_ret, signed=True)
        dd_str = _fmt_pct(max_dd)
        summary_rows.append(
            f"<tr><td><strong>{html.escape(ticker)}</strong></td>"
            f"<td>{html.escape(underlying)}</td>"
            f'<td><span class="badge badge-gray">'
            f"{html.escape(stype_label)}</span></td>"
            f'<td class="num">{threshold}</td>'
            f'<td class="num">{_fmt_pct(profit_target)}</td>'
            f'<td class="num">{trade_count}</td>'
            f'<td class="num">{html.escape(sharpe_str)}</td>'
            f'<td class="num">{html.escape(wr_str)}</td>'
            f'<td class="num {ret_cls}">{html.escape(ret_str)}</td>'
            f'<td class="num">{html.escape(dd_str)}</td></tr>',
        )

        # Individual trade rows
        if isinstance(trades, list):
            for i, t in enumerate(trades):
                if not isinstance(t, dict):
                    continue
                t_ret = t.get("leveraged_return", 0)
                t_cls = _pct_class(t_ret)
                win = isinstance(t_ret, (int, float)) and t_ret > 0
                reason = str(t.get("exit_reason", ""))
                reason_badge = _badge(
                    "TARGET"
                    if reason == "target"
                    else "ALERT"
                    if reason == "stop"
                    else "WATCH",
                )
                dd_entry = t.get("drawdown_at_entry", 0)
                entry_dt = t.get("entry_date") or str(t.get("entry_day", ""))
                exit_dt = t.get("exit_date") or str(t.get("exit_day", ""))
                all_rows.append(
                    f"<tr>"
                    f"<td>{html.escape(ticker)}</td>"
                    f"<td>{html.escape(stype_label)}</td>"
                    f'<td class="num">{i + 1}</td>'
                    f'<td class="num">{html.escape(entry_dt)}</td>'
                    f'<td class="num">{html.escape(exit_dt)}</td>'
                    f'<td class="num">${t.get("entry_price", 0):.2f}</td>'
                    f'<td class="num">${t.get("exit_price", 0):.2f}</td>'
                    f'<td class="num">{_fmt_pct(dd_entry)}</td>'
                    f'<td class="num {t_cls}">'
                    f"{_fmt_pct(t_ret, signed=True)}</td>"
                    f"<td>{reason_badge}</td>"
                    f"<td>{'W' if win else 'L'}</td>"
                    f"</tr>",
                )

    if not chart_datasets:
        return ""

    # Find max labels length for chart
    max_labels = 0
    for etf in data:
        if isinstance(etf, dict):
            eq = etf.get("equity_curve", [])
            if isinstance(eq, list) and len(eq) > max_labels:
                max_labels = len(eq)
    labels_json = json.dumps(list(range(max_labels)))

    chart_js = (
        "<script>\n"
        "const ctx = document.getElementById('equityChart').getContext('2d');\n"
        "new Chart(ctx, {\n"
        "  type: 'line',\n"
        "  data: {\n"
        f"    labels: {labels_json},\n"
        "    datasets: [\n      " + ",\n      ".join(chart_datasets) + "\n    ]\n"
        "  },\n"
        "  options: {\n"
        "    responsive: true,\n"
        "    maintainAspectRatio: false,\n"
        "    interaction: { mode: 'index', intersect: false },\n"
        "    plugins: {\n"
        "      title: { display: true,"
        " text: 'Equity Curve — $10,000 Starting Capital',"
        " color: '#e6edf3',"
        " font: { size: 16, family: 'Inter' } },\n"
        "      tooltip: {\n"
        "        callbacks: {\n"
        "          label: function(ctx) {\n"
        "            return ctx.dataset.label + ': $' +"
        " ctx.parsed.y.toLocaleString();\n"
        "          }\n"
        "        }\n"
        "      }\n"
        "    },\n"
        "    scales: {\n"
        "      x: { title: { display: true, text: 'Trade #',"
        " color: '#8b949e' },"
        " ticks: { maxTicksLimit: 20, color: '#8b949e' },"
        " grid: { color: '#2a3346' } },\n"
        "      y: { title: { display: true, text: 'Portfolio Value ($)',"
        " color: '#8b949e' },"
        " ticks: { color: '#8b949e', callback: function(v) {"
        " return '$' + v.toLocaleString(); } },"
        " grid: { color: '#2a3346' } }\n"
        "    }\n"
        "  }\n"
        "});\n"
        "</script>\n"
    )

    top_bar = _page_header_bar(
        report_date, "trade-log", report_dates, page_prefix="trade-log-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    summary_table = (
        "<section>\n"
        "<h2>Strategy Performance Summary</h2>\n"
        '<div class="card">\n'
        "<p>Each ETF is backtested across 4 strategy types "
        "(ATH mean-reversion, RSI oversold, Bollinger band, MA dip) "
        "over 2 years of historical data. Exits at profit target or stop loss.</p>\n"
        '<table class="mt-12">\n<thead><tr>'
        '<th scope="col">ETF</th>'
        '<th scope="col">Underlying</th>'
        '<th scope="col">Strategy</th>'
        '<th scope="col" class="num">Entry</th>'
        '<th scope="col" class="num">Target</th>'
        '<th scope="col" class="num">Trades</th>'
        '<th scope="col" class="num">Sharpe</th>'
        '<th scope="col" class="num">Win Rate</th>'
        '<th scope="col" class="num">Return</th>'
        '<th scope="col" class="num">Max DD</th>'
        "</tr></thead>\n<tbody>\n"
        + "\n".join(summary_rows)
        + "\n</tbody></table>\n</div>\n</section>\n"
    )

    chart_section = (
        "<section>\n"
        "<h2>Equity Curve</h2>\n"
        '<div class="card">\n'
        '<div style="position:relative;height:450px">\n'
        '<canvas id="equityChart"></canvas>\n'
        "</div>\n</div>\n</section>\n"
    )

    trade_count = len(all_rows)
    trade_table = (
        "<section>\n"
        "<details>\n"
        "<summary>"
        '<h2 style="display:inline">Individual Trade Log</h2> '
        f'<span class="badge badge-gray">{trade_count} trades</span>'
        "</summary>\n"
        '<div class="card">\n'
        '<table class="mt-12">\n<thead><tr>'
        '<th scope="col">ETF</th>'
        '<th scope="col">Strategy</th>'
        '<th scope="col" class="num">#</th>'
        '<th scope="col">Entry Date</th>'
        '<th scope="col">Exit Date</th>'
        '<th scope="col" class="num">Entry $</th>'
        '<th scope="col" class="num">Exit $</th>'
        '<th scope="col" class="num">DD at Entry</th>'
        '<th scope="col" class="num">Return</th>'
        '<th scope="col">Exit Reason</th>'
        '<th scope="col">W/L</th>'
        "</tr></thead>\n<tbody>\n"
        + "\n".join(all_rows)
        + "\n</tbody></table>\n</div>\n"
        "</details>\n</section>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "backtested, not live trades.</span>\n"
        "</footer>\n"
    )

    portfolio_trades = _section_trade_history()

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        portfolio_trades,
        chart_section,
        summary_table,
        trade_table,
        "</main>\n",
        footer,
    ]

    chart_cdn = (
        '<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist'
        '/chart.umd.min.js"></script>\n'
    )

    # Insert Chart.js CDN before </head> and chart script before </body>
    return (
        _html_page(
            title=f"Trade Log {report_date}",
            body="\n".join(p for p in body_parts if p),
            description="Trade history, backtest logs and equity curves",
        )
        .replace("</head>", f"{chart_cdn}</head>", 1)
        .replace("</body>", f"{chart_js}</body>", 1)
    )


def build_forecasts_html(
    outputs: dict[str, str],
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build the forecasts page with entry probability table and accuracy KPIs."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    forecast_raw = _parse_output(outputs.get("strategy.forecast", ""))
    accuracy_raw = _parse_output(outputs.get("strategy.verify", ""))

    # Parse forecasts
    forecasts: list[dict[str, object]] = []
    actionable_count = 0
    if isinstance(forecast_raw, dict):
        fc_list = forecast_raw.get("forecasts", [])
        if isinstance(fc_list, list):
            forecasts = [f for f in fc_list if isinstance(f, dict)]
        ac_raw = forecast_raw.get("actionable_count", 0)
        actionable_count = int(ac_raw) if isinstance(ac_raw, (int, float)) else 0

    if not forecasts:
        return ""

    # Parse accuracy data
    accuracy: dict[str, object] = {}
    if isinstance(accuracy_raw, dict):
        accuracy = accuracy_raw

    # Build accuracy KPI strip — or disclaimer if no verified trades yet
    accuracy_section = ""
    tv_raw = accuracy.get("total_verifications", 0)
    total_verif = int(tv_raw) if isinstance(tv_raw, (int, float)) else 0
    if total_verif == 0:
        accuracy_section = (
            "<section>\n"
            '<div style="background:var(--warning-bg);border:1px solid var(--warning);'
            "border-radius:8px;padding:16px 20px;margin-bottom:24px;"
            'display:flex;align-items:flex-start;gap:12px;">\n'
            '<span style="font-size:20px;line-height:1;">&#9888;</span>\n'
            "<div>\n"
            '<strong style="color:var(--warning);">No verified trades yet</strong>'
            '<p style="margin:4px 0 0;color:var(--text-secondary);font-size:14px;">'
            "Forecast accuracy requires real trade outcomes to measure against. "
            "The probabilities below are model estimates based on signal state, "
            "backtest win rates, and confidence factors &mdash; they have not been "
            "validated with actual trades. Accuracy metrics will appear here "
            "once positions are opened and resolved.</p>\n"
            "</div>\n</div>\n</section>\n"
        )
    if total_verif > 0:
        hr_raw = accuracy.get("hit_rate", 0)
        hit_rate = float(hr_raw) if isinstance(hr_raw, (int, float)) else 0.0
        recent_rate = accuracy.get("recent_hit_rate")
        trend = str(accuracy.get("trend", "INSUFFICIENT"))

        trend_badge_map: dict[str, str] = {
            "IMPROVING": "TARGET",
            "DECLINING": "ALERT",
            "STABLE": "WATCH",
            "INSUFFICIENT": "WATCH",
        }
        trend_badge = _badge(trend_badge_map.get(trend, "WATCH"))

        kpis = [
            '<div class="kpi-card">'
            f'<div class="kpi-value">{_fmt_pct(hit_rate)}</div>'
            '<div class="kpi-label">Hit Rate</div></div>',
            '<div class="kpi-card">'
            f'<div class="kpi-value">{total_verif}</div>'
            '<div class="kpi-label">Verifications</div></div>',
        ]
        if isinstance(recent_rate, (int, float)):
            kpis.append(
                '<div class="kpi-card">'
                f'<div class="kpi-value">{_fmt_pct(recent_rate)}</div>'
                '<div class="kpi-label">Recent (10)</div></div>',
            )
        kpis.append(
            '<div class="kpi-card">'
            f'<div class="kpi-value">{trend_badge}</div>'
            '<div class="kpi-label">Trend</div></div>',
        )
        accuracy_section = (
            "<section>\n"
            "<h2>Forecast Accuracy</h2>\n"
            '<div class="kpi-strip">\n' + "\n".join(kpis) + "\n</div>\n</section>\n"
        )

    # Build forecast table rows
    strat_short: dict[str, str] = {
        "ath_mean_reversion": "ATH",
        "rsi_oversold": "RSI",
        "bollinger_lower": "Bollinger",
        "ma_dip": "MA Dip",
    }
    forecast_rows: list[str] = []
    for fc in forecasts:
        ticker = str(fc.get("leveraged_ticker", "?"))
        state = str(fc.get("signal_state", "WATCH"))
        dd_raw = fc.get("current_drawdown_pct", 0)
        drawdown = float(dd_raw) if isinstance(dd_raw, (int, float)) else 0.0
        confidence = str(fc.get("confidence_level", "LOW"))
        ep_raw = fc.get("entry_probability", 0)
        entry_prob = float(ep_raw) if isinstance(ep_raw, (int, float)) else 0.0
        er_raw = fc.get("expected_return_pct", 0)
        exp_ret = float(er_raw) if isinstance(er_raw, (int, float)) else 0.0
        hd_raw = fc.get("expected_hold_days", 0)
        hold_days = int(hd_raw) if isinstance(hd_raw, (int, float)) else 0
        strategy = str(fc.get("best_strategy", "ath_mean_reversion"))
        stype_label = strat_short.get(strategy, strategy)

        state_badge = _badge(
            "TARGET"
            if state in ("SIGNAL", "ACTIVE", "TARGET")
            else "ALERT"
            if state == "ALERT"
            else "WATCH",
        )
        conf_badge = _badge(
            "TARGET"
            if confidence == "HIGH"
            else "ALERT"
            if confidence == "MEDIUM"
            else "WATCH",
        )
        prob_cls = _pct_class(entry_prob - 0.5)  # green if >50%, red if <50%

        forecast_rows.append(
            f"<tr>"
            f"<td><strong>{html.escape(ticker)}</strong></td>"
            f"<td>{state_badge} {html.escape(state)}</td>"
            f'<td class="num">{_fmt_pct(abs(drawdown))}</td>'
            f"<td>{conf_badge}</td>"
            f'<td class="num {prob_cls}">{_fmt_pct(entry_prob)}</td>'
            f'<td class="num {_pct_class(exp_ret)}">'
            f"{_fmt_pct(exp_ret, signed=True)}</td>"
            f'<td class="num">{hold_days}d</td>'
            f"<td>{_strategy_badge(strategy, stype_label)}</td>"
            f"</tr>",
        )

    top_bar = _page_header_bar(
        report_date, "forecasts", report_dates, page_prefix="forecasts-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        '<div class="header-status">'
        f'<span class="ok">{actionable_count}</span> actionable'
        f" / {len(forecasts)} total"
        "</div>\n</header>\n"
    )

    forecast_table = (
        "<section>\n"
        "<h2>ETF Forecasts</h2>\n"
        '<div class="card">\n'
        "<p>Entry probability estimates based on signal state, "
        "confidence factors, and historical backtest win rates. "
        "Expected returns blend probability with average gain/loss.</p>\n"
        '<table class="mt-12">\n<thead><tr>'
        '<th scope="col">ETF</th>'
        '<th scope="col">Signal</th>'
        '<th scope="col" class="num">Drawdown</th>'
        '<th scope="col">Confidence</th>'
        '<th scope="col" class="num">Entry Prob</th>'
        '<th scope="col" class="num">Exp Return</th>'
        '<th scope="col" class="num">Hold Time</th>'
        '<th scope="col">Strategy</th>'
        "</tr></thead>\n<tbody>\n"
        + "\n".join(forecast_rows)
        + "\n</tbody></table>\n</div>\n</section>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "forecasts are probabilistic, not guarantees.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        accuracy_section,
        forecast_table,
        "</main>\n",
        footer,
    ]

    return _html_page(
        title=f"Forecasts {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"ETF entry probability forecasts for {report_date}",
    )


# ---------------------------------------------------------------------------
# Company page — sprint board, roadmap, ceremonies, budget, pipeline health
# ---------------------------------------------------------------------------

_KANBAN_COLS = ["TODO", "IN_PROGRESS", "DONE", "BLOCKED"]
_KANBAN_LABELS = {
    "TODO": "To Do",
    "IN_PROGRESS": "In Progress",
    "DONE": "Done",
    "BLOCKED": "Blocked",
}


def _section_sprint_board() -> str:
    """Render current sprint as a kanban board."""
    sprint = get_current_sprint()
    if sprint is None:
        return (
            "<section>\n<h2>Sprint Board</h2>\n"
            '<div class="card"><p class="text-muted">'
            "No active sprint &mdash; run "
            "<code>uv run python -m app.agile init</code></p></div>\n"
            "</section>\n"
        )

    status_badge = _badge(
        "TARGET"
        if sprint.status == "ACTIVE"
        else "WATCH"
        if sprint.status == "PLANNED"
        else "ALERT",
    )
    goals_html = ""
    if sprint.goals:
        items = "".join(f"<li>{html.escape(g)}</li>" for g in sprint.goals)
        goals_html = f'<ul class="sprint-goals">{items}</ul>'

    # Group tasks by status
    by_status: dict[str, list[str]] = {c: [] for c in _KANBAN_COLS}
    for task in sprint.tasks:
        ts = task.status
        status_val = ts.value if hasattr(ts, "value") else str(ts)
        col = status_val if status_val in by_status else "TODO"
        tp = task.priority
        prio_val = tp.value if hasattr(tp, "value") else str(tp)
        prio = prio_val.lower()
        card = (
            f'<div class="kanban-card priority-{html.escape(prio)}">'
            f'<span class="task-id">{html.escape(task.id)}</span>'
            f'<div class="task-title">{html.escape(task.title)}</div>'
            f'<span class="task-dept">{html.escape(task.assignee_department)}</span>'
            "</div>"
        )
        by_status[col].append(card)

    cols_html = ""
    for col_key in _KANBAN_COLS:
        label = _KANBAN_LABELS.get(col_key, col_key)
        cards = "".join(by_status[col_key]) or (
            '<p style="font-size:12px;color:var(--text-muted)">No tasks</p>'
        )
        cols_html += (
            f'<div class="kanban-column"><h3>{html.escape(label)}</h3>{cards}</div>\n'
        )

    task_done = sum(
        1 for t in sprint.tasks
        if (t.status.value if hasattr(t.status, "value") else str(t.status)) == "DONE"
    )
    task_total = len(sprint.tasks)

    return (
        "<section>\n"
        "<h2>Sprint Board</h2>\n"
        '<div class="card">\n'
        f"<p><strong>Sprint {sprint.number}</strong> "
        f"({html.escape(sprint.start_date)} &rarr; "
        f"{html.escape(sprint.end_date)}) "
        f"{status_badge} &bull; "
        f"{task_done}/{task_total} tasks done</p>\n"
        f"{goals_html}"
        f'<div class="kanban-board">{cols_html}</div>\n'
        "</div>\n</section>\n"
    )


def _section_ceremonies() -> str:
    """Render recent standups and latest retrospective."""
    parts: list[str] = []

    # Recent standups
    standup_dates = list_standups()
    recent_dates = standup_dates[-3:] if standup_dates else []
    standup_html = ""
    for d in reversed(recent_dates):
        record = load_standup(d)
        if record is None:
            continue
        entries_html = ""
        for e in record.entries:
            entries_html += (
                f'<div class="standup-entry">'
                f'<div class="dept">{html.escape(e.department)}'
                f" ({html.escape(e.agent)})</div>"
                f'<div class="field">Yesterday: '
                f"<span>{html.escape(e.yesterday)}</span></div>"
                f'<div class="field">Today: '
                f"<span>{html.escape(e.today)}</span></div>"
                f'<div class="field">Blockers: '
                f"<span>{html.escape(e.blockers or 'None')}</span></div>"
                f"</div>"
            )
        standup_html += (
            f'<details class="standup-detail">'
            f"<summary>Standup &mdash; {html.escape(d)}"
            f" ({html.escape(record.session)})</summary>"
            f'<div class="standup-entries">{entries_html}</div>'
            f"</details>"
        )

    if standup_html:
        parts.append(
            "<h3>Recent Standups</h3>\n" + standup_html,
        )

    # Latest retrospective
    retro_nums = list_retros()
    if retro_nums:
        retro = load_retro(retro_nums[-1])
        if retro is not None:
            ww = (
                "".join(
                    f'<div class="ceremony-item">{html.escape(i.text)}</div>'
                    for i in retro.went_well
                )
                or '<p class="text-muted">None recorded</p>'
            )
            ti = (
                "".join(
                    f'<div class="ceremony-item">{html.escape(i.text)}</div>'
                    for i in retro.to_improve
                )
                or '<p class="text-muted">None recorded</p>'
            )
            ai = (
                "".join(
                    f'<div class="ceremony-item">{html.escape(i.text)}</div>'
                    for i in retro.action_items
                )
                or '<p class="text-muted">None recorded</p>'
            )
            parts.append(
                f"<h3>Sprint {retro.sprint_number} Retrospective</h3>\n"
                f'<div class="ceremony-grid">'
                f'<div class="ceremony-col went-well">'
                f"<h3>Went Well</h3>{ww}</div>"
                f'<div class="ceremony-col to-improve">'
                f"<h3>To Improve</h3>{ti}</div>"
                f'<div class="ceremony-col action-items">'
                f"<h3>Action Items</h3>{ai}</div>"
                f"</div>",
            )

    if not parts:
        return (
            "<section>\n<h2>Ceremonies</h2>\n"
            '<div class="card"><p class="text-muted">'
            "No ceremonies recorded yet</p></div>\n</section>\n"
        )

    return (
        "<section>\n<h2>Ceremonies</h2>\n"
        '<div class="card">\n' + "\n".join(parts) + "\n</div>\n</section>\n"
    )


def _section_token_budget() -> str:
    """Render department token budget vs spend bars."""
    try:
        from app.finops.budget import load_budgets
        from app.finops.tracker import summarize_period
    except ImportError:
        return ""

    config = load_budgets()
    if not config.budgets:
        return (
            "<section>\n<h2>Token Budget</h2>\n"
            '<div class="card"><p class="text-muted">'
            "No budget configured &mdash; run "
            "<code>uv run python -m app.finops init</code></p></div>\n"
            "</section>\n"
        )

    # Get current week spend
    from datetime import UTC, datetime, timedelta

    now = datetime.now(tz=UTC)
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")
    summary = summarize_period(week_start, week_end)
    dept_spend = summary.by_department

    rows_html = ""
    for b in config.budgets:
        spent = dept_spend.get(b.department, 0.0)
        pct = (spent / b.weekly_budget_usd * 100) if b.weekly_budget_usd > 0 else 0
        bar_cls = "green" if pct < 75 else "yellow" if pct < 90 else "red"
        fill_w = min(pct, 100)
        prio_badge = _badge(
            "ALERT"
            if b.priority == "critical"
            else "WATCH"
            if b.priority == "normal"
            else "TARGET",
        )
        rows_html += (
            f'<div class="budget-row">'
            f'<span class="dept-name">'
            f"{html.escape(b.department.title())} {prio_badge}</span>"
            f'<span class="budget-bar-wrap">'
            f'<div class="progress-bar">'
            f'<div class="progress-fill {bar_cls}" '
            f'style="width:{fill_w:.0f}%"></div></div></span>'
            f'<span class="budget-nums">'
            f"${spent:.2f} / ${b.weekly_budget_usd:.2f}"
            f" ({pct:.0f}%)</span>"
            f"</div>"
        )

    total_spent = sum(dept_spend.values())
    total_budget = config.total_weekly_usd
    total_pct = (total_spent / total_budget * 100) if total_budget > 0 else 0

    return (
        "<section>\n<h2>Token Budget (Weekly)</h2>\n"
        '<div class="card">\n'
        f"{rows_html}"
        f'<div class="budget-row" style="border-top:2px solid '
        f'var(--border-primary);margin-top:8px;padding-top:10px">'
        f'<span class="dept-name"><strong>Total</strong></span>'
        f'<span class="budget-bar-wrap"></span>'
        f'<span class="budget-nums"><strong>'
        f"${total_spent:.2f} / ${total_budget:.2f}"
        f" ({total_pct:.0f}%)</strong></span>"
        f"</div>"
        "\n</div>\n</section>\n"
    )


def _section_pipeline_health() -> str:
    """Render pipeline health with grade badge and module grid."""
    health = get_system_health()
    modules = get_all_module_health()

    if health.module_count == 0 and not modules:
        return (
            "<section>\n<h2>Pipeline Health</h2>\n"
            '<div class="card"><p class="text-muted">'
            "No pipeline data recorded yet</p></div>\n</section>\n"
        )

    grade_cls = f"grade-{health.grade}"
    trend_arrows = {"improving": "&uarr;", "stable": "&rarr;", "degrading": "&darr;"}

    module_cards = ""
    for m in modules:
        trend_arrow = trend_arrows.get(m.trend, "&rarr;")
        trend_cls = f"trend-{m.trend}"
        sr_cls = (
            "green"
            if m.success_rate_7d >= 0.9
            else ("yellow" if m.success_rate_7d >= 0.7 else "red")
        )
        module_cards += (
            f'<div class="health-card {trend_cls}">'
            f'<div class="module-name">{html.escape(m.name)}</div>'
            f'<div class="health-stat">'
            f"<span>Success (7d)</span>"
            f'<span class="val {sr_cls}">'
            f"{m.success_rate_7d:.0%}</span></div>"
            f'<div class="health-stat">'
            f"<span>Avg Duration</span>"
            f'<span class="val">{m.avg_duration_seconds:.1f}s</span></div>'
            f'<div class="health-stat">'
            f"<span>Trend</span>"
            f'<span class="val">{trend_arrow} '
            f"{html.escape(m.trend)}</span></div>"
            f"</div>"
        )

    return (
        "<section>\n<h2>Pipeline Health</h2>\n"
        '<div class="card">\n'
        f'<div style="display:flex;align-items:center;gap:16px;'
        f'margin-bottom:16px">'
        f'<span class="grade-badge {grade_cls}">'
        f"{html.escape(health.grade)}</span>"
        f"<div>"
        f'<div style="font-size:18px;color:var(--text-primary)">'
        f"System Health: {health.score:.0%}</div>"
        f'<div style="font-size:13px;color:var(--text-muted)">'
        f"{health.module_count} modules tracked</div>"
        f"</div></div>"
        f'<div class="health-grid">{module_cards}</div>'
        "\n</div>\n</section>\n"
    )


def build_sprint_board_html(
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build sprint board page with kanban board and ceremonies."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    sprint_board = _section_sprint_board()
    ceremonies = _section_ceremonies()

    top_bar = _page_header_bar(
        report_date, "sprint-board", report_dates, page_prefix="sprint-board-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "sprint board &amp; ceremonies.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        sprint_board,
        ceremonies,
        "</main>\n",
        footer,
    ]

    return _html_page(
        title=f"Sprint Board {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"Sprint board and ceremonies for {report_date}",
    )


def build_system_health_html(
    run: SchedulerRun | None = None,
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build system health page with pipeline and token budget."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    pipeline = _section_pipeline_health()
    token_budget = _section_token_budget()
    modules = _section_module_status(run) if run else ""

    top_bar = _page_header_bar(
        report_date, "system-health", report_dates, page_prefix="system-health-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "system health &amp; operations.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        pipeline,
        token_budget,
        modules,
        "</main>\n",
        footer,
    ]

    return _html_page(
        title=f"System Health {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"System health and operations for {report_date}",
    )


# ---------------------------------------------------------------------------
# Strategies page — strategy type comparison and rankings
# ---------------------------------------------------------------------------


def _parse_backtest_data(
    outputs: dict[str, str],
) -> list[dict[str, object]]:
    """Parse strategy.backtest-all output into a list of ETF dicts."""
    data = _parse_output(outputs.get("strategy.backtest-all", ""))
    if not isinstance(data, list):
        return []
    return [e for e in data if isinstance(e, dict)]


_STRAT_LABELS: dict[str, str] = {
    "ath_mean_reversion": "ATH Mean-Reversion",
    "rsi_oversold": "RSI Oversold",
    "bollinger_lower": "Bollinger Band",
    "ma_dip": "MA Dip",
}


def _section_strategy_comparison(
    data: list[dict[str, object]],
) -> str:
    """Aggregate performance by strategy type across all ETFs."""
    if not data:
        return ""

    # Aggregate by strategy type
    by_type: dict[str, list[dict[str, object]]] = {}
    for etf in data:
        stype = str(etf.get("strategy_type", "ath_mean_reversion"))
        by_type.setdefault(stype, []).append(etf)

    _row_type = tuple[str, str, float, float, float, int, str, str]
    rows: list[_row_type] = []
    best_sharpe = -999.0
    best_type = ""

    for stype, etfs in sorted(by_type.items()):
        label = _STRAT_LABELS.get(stype, stype)
        sharpes: list[float] = [
            float(v)
            for e in etfs
            if isinstance((v := e.get("sharpe_ratio")), (int, float))
        ]
        win_rates: list[float] = [
            float(v) for e in etfs if isinstance((v := e.get("win_rate")), (int, float))
        ]
        returns: list[float] = [
            float(v)
            for e in etfs
            if isinstance((v := e.get("total_return")), (int, float))
        ]
        trades = sum(
            int(tc)
            for e in etfs
            if isinstance((tc := e.get("trade_count", 0)), (int, float))
        )

        avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0.0
        avg_wr = sum(win_rates) / len(win_rates) if win_rates else 0.0
        avg_ret = sum(returns) / len(returns) if returns else 0.0

        if avg_sharpe > best_sharpe:
            best_sharpe = avg_sharpe
            best_type = stype

        # Find best ETF for this strategy
        def _sharpe_key(e: dict[str, object]) -> float:
            s = e.get("sharpe_ratio", 0)
            return float(s) if isinstance(s, (int, float)) else 0.0

        best_etf = max(etfs, key=_sharpe_key)
        best_ticker = str(best_etf.get("leveraged_ticker", "?"))

        ret_cls = _pct_class(avg_ret)
        rows.append(
            (stype, label, avg_sharpe, avg_wr, avg_ret, trades, best_ticker, ret_cls),
        )

    table_rows = ""
    for row in rows:
        r_stype, r_label, r_sharpe, r_wr, r_ret, r_trades, r_tk, r_cls = row
        best_mark = (
            ' <span class="badge badge-ok">BEST</span>' if r_stype == best_type else ""
        )
        table_rows += (
            f"<tr><td><strong>{html.escape(r_label)}</strong>"
            f"{best_mark}</td>"
            f'<td class="num">{r_sharpe:.3f}</td>'
            f'<td class="num">{_fmt_pct(r_wr)}</td>'
            f'<td class="num {r_cls}">'
            f"{_fmt_pct(r_ret, signed=True)}</td>"
            f'<td class="num">{r_trades}</td>'
            f"<td>{html.escape(r_tk)}</td></tr>\n"
        )

    return (
        "<section>\n"
        "<h2>Strategy Type Comparison</h2>\n"
        '<div class="card">\n'
        "<p>Performance metrics averaged across all ETFs "
        "for each strategy type.</p>\n"
        '<table class="mt-12">\n<thead><tr>'
        '<th scope="col">Strategy</th>'
        '<th scope="col" class="num">Avg Sharpe</th>'
        '<th scope="col" class="num">Avg Win Rate</th>'
        '<th scope="col" class="num">Avg Return</th>'
        '<th scope="col" class="num">Total Trades</th>'
        '<th scope="col">Best ETF</th>'
        "</tr></thead>\n<tbody>\n"
        + table_rows
        + "</tbody></table>\n</div>\n</section>\n"
    )


def _section_strategy_rankings(
    data: list[dict[str, object]],
) -> str:
    """Rank ETFs by their best strategy performance."""
    if not data:
        return ""

    # Find best strategy per ETF (by Sharpe)
    by_etf: dict[str, dict[str, object]] = {}
    for etf in data:
        ticker = str(etf.get("leveraged_ticker", "?"))
        sharpe = etf.get("sharpe_ratio", 0)
        if not isinstance(sharpe, (int, float)):
            sharpe = 0
        existing = by_etf.get(ticker)
        if existing is None:
            by_etf[ticker] = etf
        else:
            ex_sharpe = existing.get("sharpe_ratio", 0)
            if not isinstance(ex_sharpe, (int, float)):
                ex_sharpe = 0
            if sharpe > ex_sharpe:
                by_etf[ticker] = etf

    # Sort by Sharpe descending
    def _rank_key(e: dict[str, object]) -> float:
        s = e.get("sharpe_ratio", 0)
        return float(s) if isinstance(s, (int, float)) else 0.0

    ranked = sorted(by_etf.values(), key=_rank_key, reverse=True)

    rows: list[str] = []
    strat_short = {
        "ath_mean_reversion": "ATH",
        "rsi_oversold": "RSI",
        "bollinger_lower": "Bollinger",
        "ma_dip": "MA Dip",
    }
    for i, etf in enumerate(ranked):
        ticker = html.escape(str(etf.get("leveraged_ticker", "?")))
        underlying = html.escape(str(etf.get("underlying_ticker", "?")))
        stype = str(etf.get("strategy_type", "ath_mean_reversion"))
        stype_label = strat_short.get(stype, stype)
        sharpe = etf.get("sharpe_ratio", 0)
        sharpe_str = f"{sharpe:.3f}" if isinstance(sharpe, (int, float)) else "N/A"
        wr = etf.get("win_rate")
        wr_str = _fmt_pct(wr) if isinstance(wr, (int, float)) else "N/A"
        ret = etf.get("total_return", 0)
        ret_str = _fmt_pct(ret, signed=True) if isinstance(ret, (int, float)) else "N/A"
        ret_cls = _pct_class(ret)
        max_dd = etf.get("max_drawdown", 0)
        dd_str = _fmt_pct(max_dd) if isinstance(max_dd, (int, float)) else "N/A"
        rank_str = f"#{i + 1}"

        rows.append(
            f"<tr><td>{rank_str}</td>"
            f"<td><strong>{ticker}</strong></td>"
            f"<td>{html.escape(underlying)}</td>"
            f"<td>{_strategy_badge(stype, stype_label)}</td>"
            f'<td class="num">{html.escape(sharpe_str)}</td>'
            f'<td class="num">{html.escape(wr_str)}</td>'
            f'<td class="num {ret_cls}">{html.escape(ret_str)}</td>'
            f'<td class="num">{html.escape(dd_str)}</td></tr>\n',
        )

    return (
        "<section>\n"
        "<h2>ETF Rankings (Best Strategy)</h2>\n"
        '<div class="card">\n'
        "<p>Each ETF ranked by its best-performing strategy "
        "(highest Sharpe ratio).</p>\n"
        '<table class="mt-12">\n<thead><tr>'
        '<th scope="col">Rank</th>'
        '<th scope="col">ETF</th>'
        '<th scope="col">Underlying</th>'
        '<th scope="col">Strategy</th>'
        '<th scope="col" class="num">Sharpe</th>'
        '<th scope="col" class="num">Win Rate</th>'
        '<th scope="col" class="num">Return</th>'
        '<th scope="col" class="num">Max DD</th>'
        "</tr></thead>\n<tbody>\n"
        + "".join(rows)
        + "</tbody></table>\n</div>\n</section>\n"
    )


def _section_strategy_equity_curves(
    data: list[dict[str, object]],
) -> tuple[str, str]:
    """Build Chart.js equity curve section for best strategy per ETF.

    Returns (section_html, chart_js_script).
    """
    if not data:
        return "", ""

    # Select best strategy per ETF by Sharpe
    by_etf: dict[str, dict[str, object]] = {}
    for etf in data:
        ticker = str(etf.get("leveraged_ticker", "?"))
        sharpe = etf.get("sharpe_ratio", 0)
        if not isinstance(sharpe, (int, float)):
            sharpe = 0
        existing = by_etf.get(ticker)
        if existing is None:
            by_etf[ticker] = etf
        else:
            ex_sharpe = existing.get("sharpe_ratio", 0)
            if not isinstance(ex_sharpe, (int, float)):
                ex_sharpe = 0
            if sharpe > ex_sharpe:
                by_etf[ticker] = etf

    strat_short = {
        "ath_mean_reversion": "ATH",
        "rsi_oversold": "RSI",
        "bollinger_lower": "Bollinger",
        "ma_dip": "MA Dip",
    }
    chart_datasets: list[str] = []
    max_labels = 0

    for idx, (ticker, etf) in enumerate(sorted(by_etf.items())):
        equity = etf.get("equity_curve", [])
        if not isinstance(equity, list) or not equity:
            continue
        stype = str(etf.get("strategy_type", "ath_mean_reversion"))
        stype_label = strat_short.get(stype, stype)
        color = _CHART_COLORS[idx % len(_CHART_COLORS)]
        chart_label = f"{ticker} ({stype_label})"
        equity_json = json.dumps(equity)

        chart_datasets.append(
            "{"
            f'label:"{html.escape(chart_label)}",'
            f"data:{equity_json},"
            f'borderColor:"{color}",'
            f'backgroundColor:"{color}22",'
            "borderWidth:2,"
            "pointRadius:3,"
            "pointHoverRadius:5,"
            "tension:0.1,"
            "fill:false"
            "}",
        )
        if len(equity) > max_labels:
            max_labels = len(equity)

    if not chart_datasets:
        return "", ""

    labels_json = json.dumps(list(range(max_labels)))

    chart_js = (
        "<script>\n"
        "const sctx = document.getElementById('stratEquityChart')"
        ".getContext('2d');\n"
        "new Chart(sctx, {\n"
        "  type: 'line',\n"
        "  data: {\n"
        f"    labels: {labels_json},\n"
        "    datasets: [\n      " + ",\n      ".join(chart_datasets) + "\n    ]\n"
        "  },\n"
        "  options: {\n"
        "    responsive: true,\n"
        "    maintainAspectRatio: false,\n"
        "    interaction: { mode: 'index', intersect: false },\n"
        "    plugins: {\n"
        "      title: { display: true,"
        " text: 'Best Strategy Equity Curve per ETF',"
        " color: '#e6edf3',"
        " font: { size: 16, family: 'Inter' } },\n"
        "      tooltip: {\n"
        "        callbacks: {\n"
        "          label: function(ctx) {\n"
        "            return ctx.dataset.label + ': $' +"
        " ctx.parsed.y.toLocaleString();\n"
        "          }\n"
        "        }\n"
        "      }\n"
        "    },\n"
        "    scales: {\n"
        "      x: { title: { display: true, text: 'Trade #',"
        " color: '#8b949e' },"
        " ticks: { maxTicksLimit: 20, color: '#8b949e' },"
        " grid: { color: '#2a3346' } },\n"
        "      y: { title: { display: true, text: 'Portfolio Value ($)',"
        " color: '#8b949e' },"
        " ticks: { color: '#8b949e', callback: function(v) {"
        " return '$' + v.toLocaleString(); } },"
        " grid: { color: '#2a3346' } }\n"
        "    }\n"
        "  }\n"
        "});\n"
        "</script>\n"
    )

    section = (
        "<section>\n"
        "<h2>Equity Curves</h2>\n"
        '<div class="card">\n'
        '<div style="position:relative;height:450px">\n'
        '<canvas id="stratEquityChart"></canvas>\n'
        "</div>\n</div>\n</section>\n"
    )

    return section, chart_js


def build_strategies_html(
    outputs: dict[str, str],
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build strategies performance page with comparison and rankings."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    data = _parse_backtest_data(outputs)
    if not data:
        return ""

    comparison = _section_strategy_comparison(data)
    chart_section, chart_js = _section_strategy_equity_curves(data)
    rankings = _section_strategy_rankings(data)

    top_bar = _page_header_bar(
        report_date, "strategies", report_dates, page_prefix="strategies-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "backtested performance, not live results.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        comparison,
        chart_section,
        rankings,
        "</main>\n",
        footer,
    ]

    chart_cdn = (
        '<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist'
        '/chart.umd.min.js"></script>\n'
    )

    result = _html_page(
        title=f"Strategies {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"Strategy performance comparison for {report_date}",
    )

    if chart_js:
        result = result.replace("</head>", f"{chart_cdn}</head>", 1).replace(
            "</body>", f"{chart_js}</body>", 1
        )

    return result


# ---------------------------------------------------------------------------
# Financials page — portfolio P&L, equity curve, operating costs
# ---------------------------------------------------------------------------


def _section_portfolio_kpis() -> str:
    """Render portfolio KPI cards."""
    try:
        from app.portfolio.tracker import PortfolioConfig, load_history
    except ImportError:
        return ""

    config = PortfolioConfig.load()
    history = load_history()

    total_return = (
        (config.total_value - 10_000.0) / 10_000.0 if config.total_value else 0
    )
    net_value = config.total_value - config.total_operating_costs
    net_return = (net_value - 10_000.0) / 10_000.0

    total_cls = "pct-up" if total_return >= 0 else "pct-down"
    net_cls = "pct-up" if net_return >= 0 else "pct-down"
    realized_cls = "pct-up" if config.realized_pl >= 0 else "pct-down"

    cards = [
        _kpi_card(
            "Portfolio Value",
            f"${config.total_value:,.2f}",
            "GREEN" if total_return >= 0 else "RED",
            sub=f'<span class="{total_cls}">{total_return:+.1%}</span> total return',
            icon_name="account_balance",
        ),
        _kpi_card(
            "Cash Balance",
            f"${config.cash_balance:,.2f}",
            "NEUTRAL",
            sub=f"{config.cash_balance / config.total_value:.0%} of portfolio"
            if config.total_value > 0
            else "",
            icon_name="payments",
        ),
        _kpi_card(
            "Realized P&L",
            f"${config.realized_pl:+,.2f}",
            "GREEN" if config.realized_pl >= 0 else "RED",
            sub=(f'<span class="{realized_cls}">from {len(history)} snapshots</span>'),
            icon_name="trending_up",
        ),
        _kpi_card(
            "Operating Costs",
            f"${config.total_operating_costs:,.2f}",
            "YELLOW" if config.total_operating_costs > 0 else "GREEN",
            sub="$100/month run rate",
            icon_name="receipt_long",
        ),
        _kpi_card(
            "Net Value",
            f"${net_value:,.2f}",
            "GREEN" if net_return >= 0 else "RED",
            sub=f'<span class="{net_cls}">{net_return:+.1%}</span> after costs',
            icon_name="savings",
        ),
        _kpi_card(
            "Open Positions",
            str(len(config.positions)),
            "NEUTRAL",
            sub=", ".join(p.ticker for p in config.positions) or "none",
            icon_name="inventory_2",
        ),
    ]

    return (
        '<section id="portfolio-kpis">\n'
        "<h2>Portfolio Overview</h2>\n"
        '<div class="kpi-strip">\n' + "\n".join(cards) + "\n</div>\n</section>\n"
    )


def _section_equity_curve() -> tuple[str, str]:
    """Render equity curve section. Returns (html, chart_js)."""
    try:
        from app.portfolio.tracker import load_history
    except ImportError:
        return "", ""

    history = load_history()
    if len(history) < 2:
        return (
            "<section>\n<h2>Equity Curve</h2>\n"
            '<div class="card"><p class="text-muted">'
            "Need at least 2 snapshots to display equity curve. "
            "Run daily to build history.</p></div>\n</section>\n"
        ), ""

    labels = [h.date for h in history]
    gross_values = [h.total_value for h in history]
    net_values = [h.net_value for h in history]
    baseline = [10_000.0] * len(history)

    import json as _json

    chart_js = (
        "<script>\n"
        "const eqCtx = document.getElementById('equityCurveChart')"
        ".getContext('2d');\n"
        "new Chart(eqCtx, {\n"
        "  type: 'line',\n"
        "  data: {\n"
        f"    labels: {_json.dumps(labels)},\n"
        "    datasets: [{\n"
        '      label: "Portfolio Value",\n'
        f"      data: {_json.dumps(gross_values)},\n"
        '      borderColor: "#2563eb",\n'
        '      backgroundColor: "#2563eb22",\n'
        "      borderWidth: 2, pointRadius: 3, tension: 0.1, fill: false\n"
        "    },{\n"
        '      label: "Net Value (after costs)",\n'
        f"      data: {_json.dumps(net_values)},\n"
        '      borderColor: "#0a7c42",\n'
        '      backgroundColor: "#0a7c4222",\n'
        "      borderWidth: 2, pointRadius: 3, tension: 0.1, fill: false\n"
        "    },{\n"
        '      label: "Initial Capital ($10K)",\n'
        f"      data: {_json.dumps(baseline)},\n"
        '      borderColor: "#94a3b8",\n'
        "      borderWidth: 1, borderDash: [5,5], pointRadius: 0,\n"
        "      fill: false\n"
        "    }]\n"
        "  },\n"
        "  options: {\n"
        "    responsive: true,\n"
        "    maintainAspectRatio: false,\n"
        "    plugins: { legend: { position: 'top' } },\n"
        "    scales: {\n"
        "      y: {\n"
        '        title: { display: true, text: "Value ($)" },\n'
        "        ticks: { callback: v => '$' + v.toLocaleString() }\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "});\n"
        "</script>\n"
    )

    chart_html = (
        "<section>\n<h2>Equity Curve</h2>\n"
        '<div class="card">\n'
        '<div style="position:relative;height:400px">\n'
        '<canvas id="equityCurveChart"></canvas>\n'
        "</div>\n</div>\n</section>\n"
    )

    return chart_html, chart_js


def _section_operating_costs() -> str:
    """Render operating costs breakdown."""
    try:
        from app.portfolio.tracker import PortfolioConfig, load_history
    except ImportError:
        return ""

    config = PortfolioConfig.load()
    history = load_history()

    monthly_cost = 100.0
    annual_cost = monthly_cost * 12
    cost_pct = (
        config.total_operating_costs / 10_000.0 * 100
        if config.total_operating_costs > 0
        else 0
    )

    # Calculate months running
    if history and len(history) >= 2:
        from datetime import UTC as _UTC
        from datetime import datetime as _dt

        first = _dt.strptime(history[0].date, "%Y-%m-%d").replace(tzinfo=_UTC)
        last = _dt.strptime(history[-1].date, "%Y-%m-%d").replace(tzinfo=_UTC)
        months = max((last - first).days / 30.0, 0.1)
        effective_monthly = config.total_operating_costs / months
    else:
        months = 0
        effective_monthly = 0

    return (
        "<section>\n<h2>Operating Costs</h2>\n"
        '<div class="card">\n'
        "<table>\n<thead><tr>"
        "<th>Metric</th><th>Value</th>"
        "</tr></thead>\n<tbody>\n"
        f"<tr><td>Monthly run rate</td>"
        f'<td class="num">${monthly_cost:,.0f}/mo</td></tr>\n'
        f"<tr><td>Annual projected</td>"
        f'<td class="num">${annual_cost:,.0f}/yr</td></tr>\n'
        f"<tr><td>Total costs to date</td>"
        f'<td class="num">${config.total_operating_costs:,.2f}</td></tr>\n'
        f"<tr><td>Cost as % of initial capital</td>"
        f'<td class="num">{cost_pct:.1f}%</td></tr>\n'
        + (
            f"<tr><td>Effective monthly cost</td>"
            f'<td class="num">${effective_monthly:,.2f}/mo</td></tr>\n'
            if months > 0
            else ""
        )
        + "</tbody>\n</table>\n</div>\n</section>\n"
    )


def _section_trade_history() -> str:
    """Render completed trades table."""
    try:
        from app.history.outcomes import get_completed_outcomes, load_outcomes
    except ImportError:
        return ""

    all_outcomes = load_outcomes()
    completed = get_completed_outcomes()

    if not all_outcomes:
        return (
            "<section>\n<h2>Trade History</h2>\n"
            '<div class="card"><p class="text-muted">'
            "No trades recorded yet. Use "
            "<code>uv run python -m app.etf enter TICKER PRICE</code>"
            " to record entries.</p></div>\n</section>\n"
        )

    rows = ""
    total_pl = 0.0
    wins = 0

    for o in completed:
        pl_pct = o.pl_pct or 0.0
        entry_val = o.entry_price
        exit_val = o.exit_price or 0.0
        pl_class = "pct-up" if pl_pct >= 0 else "pct-down"
        if o.win:
            wins += 1
        total_pl += pl_pct

        rows += (
            "<tr>"
            f"<td>{html.escape(o.leveraged_ticker)}</td>"
            f"<td>{html.escape(o.entry_date[:10])}</td>"
            f"<td>{html.escape((o.exit_date or '')[:10])}</td>"
            f'<td class="num">${entry_val:,.2f}</td>'
            f'<td class="num">${exit_val:,.2f}</td>'
            f'<td class="num {pl_class}">{pl_pct:+.1%}</td>'
            f"<td>{'W' if o.win else 'L'}</td>"
            "</tr>\n"
        )

    # Open positions
    open_trades = [o for o in all_outcomes if o.exit_date is None]
    for o in open_trades:
        rows += (
            "<tr>"
            f"<td>{html.escape(o.leveraged_ticker)}</td>"
            f"<td>{html.escape(o.entry_date[:10])}</td>"
            f"<td>—</td>"
            f'<td class="num">${o.entry_price:,.2f}</td>'
            f"<td>—</td><td>—</td>"
            f'<td><span class="badge badge-blue">OPEN</span></td>'
            "</tr>\n"
        )

    win_rate = wins / len(completed) * 100 if completed else 0
    avg_pl = total_pl / len(completed) if completed else 0

    summary = (
        '<div class="kpi-strip" style="margin-bottom:16px">\n'
        + _kpi_card(
            "Total Trades",
            str(len(completed)),
            "NEUTRAL",
            sub=f"{len(open_trades)} open",
        )
        + _kpi_card(
            "Win Rate",
            f"{win_rate:.0f}%",
            "GREEN" if win_rate >= 50 else "RED",
            sub=f"{wins}W / {len(completed) - wins}L",
        )
        + _kpi_card(
            "Avg P&L",
            f"{avg_pl:+.1%}",
            "GREEN" if avg_pl >= 0 else "RED",
        )
        + "\n</div>\n"
    )

    return (
        "<section>\n<h2>Trade History</h2>\n" + summary + '<div class="card">\n'
        "<table>\n<thead><tr>"
        "<th>Ticker</th><th>Entry Date</th><th>Exit Date</th>"
        "<th>Entry $</th><th>Exit $</th><th>P&L</th><th>Result</th>"
        "</tr></thead>\n<tbody>\n" + rows + "</tbody>\n</table>\n</div>\n</section>\n"
    )


def _section_monthly_summary() -> str:
    """Render monthly P&L breakdown from portfolio history."""
    try:
        from app.portfolio.tracker import load_history
    except ImportError:
        return ""

    history = load_history()
    if not history:
        return ""

    # Group snapshots by month
    from app.portfolio.tracker import PortfolioSnapshot

    months: dict[str, list[PortfolioSnapshot]] = {}
    for s in history:
        month_key = s.date[:7]  # YYYY-MM
        months.setdefault(month_key, []).append(s)

    rows = ""
    prev_end_value = 10_000.0
    for month_key in sorted(months):
        snaps = months[month_key]
        start_val = snaps[0].total_value
        end_val = snaps[-1].total_value
        end_costs = snaps[-1].operating_costs_cumulative
        end_realized = snaps[-1].realized_pl_cumulative
        change = end_val - prev_end_value
        change_pct = change / prev_end_value if prev_end_value > 0 else 0
        change_cls = "pct-up" if change >= 0 else "pct-down"

        rows += (
            "<tr>"
            f"<td>{html.escape(month_key)}</td>"
            f'<td class="num">${start_val:,.2f}</td>'
            f'<td class="num">${end_val:,.2f}</td>'
            f'<td class="num {change_cls}">${change:+,.2f}</td>'
            f'<td class="num {change_cls}">{change_pct:+.1%}</td>'
            f'<td class="num">${end_realized:+,.2f}</td>'
            f'<td class="num">${end_costs:,.2f}</td>'
            "</tr>\n"
        )
        prev_end_value = end_val

    return (
        "<section>\n<h2>Monthly Summary</h2>\n"
        '<div class="card">\n'
        "<table>\n<thead><tr>"
        "<th>Month</th><th>Start</th><th>End</th>"
        "<th>Change $</th><th>Change %</th>"
        "<th>Realized P&L</th><th>Costs</th>"
        "</tr></thead>\n<tbody>\n" + rows + "</tbody>\n</table>\n</div>\n</section>\n"
    )


def build_financials_html(
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build financials page with portfolio P&L, equity curve, costs."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    kpis = _section_portfolio_kpis()
    equity_html, equity_js = _section_equity_curve()
    costs = _section_operating_costs()
    monthly = _section_monthly_summary()

    top_bar = _page_header_bar(
        report_date, "financials", report_dates, page_prefix="financials-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "portfolio financials &amp; performance.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        kpis,
        equity_html,
        costs,
        monthly,
        "</main>\n",
        footer,
    ]

    chart_cdn = (
        '<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist'
        '/chart.umd.min.js"></script>\n'
    )

    result = _html_page(
        title=f"Financials {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"Portfolio financial performance for {report_date}",
    )

    if equity_js:
        result = result.replace("</head>", f"{chart_cdn}</head>", 1).replace(
            "</body>", f"{equity_js}</body>", 1
        )

    return result


# ---------------------------------------------------------------------------
# About page — company overview, strategy, org chart, team roster
# ---------------------------------------------------------------------------


def _section_about_hero() -> str:
    """Render hero section with mission and strategy overview."""
    return (
        '<section id="about-hero">\n'
        "<h2>About This System</h2>\n"
        '<div class="card">\n'
        "<p><strong>AI-Powered Leveraged ETF Mean-Reversion "
        "Swing Trading System</strong></p>\n"
        "<p>This is a fully automated financial analysis platform that "
        "monitors underlying index drawdowns from all-time highs, "
        "identifies mean-reversion entry opportunities in leveraged ETFs, "
        "and takes profit at predetermined targets.</p>\n"
        '<p style="margin-top:12px"><strong>Core Strategy:</strong> '
        "When an underlying index drops significantly from its ATH, "
        "history shows it tends to recover. We buy the leveraged ETF "
        "during the dip and sell when it recovers for amplified returns."
        "</p>\n"
        '<p style="margin-top:12px"><strong>Initial Capital:</strong> '
        "$10,000 &bull; <strong>Operating Cost:</strong> $100/month "
        "&bull; <strong>Analysis Frequency:</strong> Twice daily "
        "(pre-market &amp; post-market)</p>\n"
        "</div>\n</section>\n"
    )


def _section_about_strategy() -> str:
    """Render strategy details: sectors, signal lifecycle, confidence."""
    # Sector-to-ETF mapping
    sectors = [
        ("Technology", "AAPL, MSFT, GOOGL, META", "TQQQ, TECL"),
        ("Semiconductors", "NVDA, AMD, AVGO", "SOXL"),
        ("Finance", "JPM, GS, BAC", "FAS"),
        ("Energy", "XOM, CVX", "UCO"),
        ("Biotech / Healthcare", "LLY, PFE, JNJ", "LABU"),
        ("Broad Market / Small Cap", "SPY, IWM", "UPRO, TNA"),
    ]
    sector_rows = ""
    for sector, tickers, etfs in sectors:
        sector_rows += (
            f"<tr><td>{html.escape(sector)}</td>"
            f"<td>{html.escape(tickers)}</td>"
            f"<td><strong>{html.escape(etfs)}</strong></td></tr>\n"
        )

    sector_table = (
        '<div class="card">\n'
        "<h3>Sector-to-ETF Mapping</h3>\n"
        "<table>\n<thead><tr>"
        "<th>Sector</th><th>Underlying Tickers</th>"
        "<th>Leveraged ETF</th>"
        "</tr></thead>\n<tbody>\n" + sector_rows + "</tbody>\n</table>\n</div>\n"
    )

    # Signal lifecycle
    states = [
        ("WATCH", "#64748b", "0-3% below ATH", "Baseline monitoring, no action"),
        (
            "ALERT",
            "#b86e00",
            "3-5% below ATH",
            "Heightened monitoring, confidence scoring begins",
        ),
        (
            "SIGNAL",
            "#c62828",
            "5%+ below ATH",
            "Entry opportunity — CIO synthesizes all domains",
        ),
        ("ACTIVE", "#2563eb", "Position entered", "Tracking P&amp;L, daily updates"),
        (
            "TARGET",
            "#0a7c42",
            "Profit target hit",
            "Exit signal, position closed, outcome recorded",
        ),
    ]
    lifecycle_items = ""
    for state, color, threshold, desc in states:
        lifecycle_items += (
            f'<div style="flex:1;min-width:140px;text-align:center;'
            f"padding:12px;border-radius:8px;"
            f'border:2px solid {color};background:{color}11">\n'
            f'<div style="font-weight:700;font-size:1.1em;'
            f'color:{color}">{state}</div>\n'
            f'<div style="font-size:0.85em;margin-top:4px;'
            f'color:#94a3b8">{threshold}</div>\n'
            f'<div style="font-size:0.8em;margin-top:6px">{desc}</div>\n'
            "</div>\n"
        )

    lifecycle_html = (
        '<div class="card">\n'
        "<h3>Signal Lifecycle</h3>\n"
        '<div style="display:flex;gap:8px;flex-wrap:wrap;'
        'align-items:stretch">\n' + lifecycle_items + "</div>\n</div>\n"
    )

    # Confidence factors
    factors = [
        "Drawdown Depth",
        "VIX Regime",
        "Fed Policy",
        "Yield Curve",
        "SEC Filings",
        "Earnings Risk",
        "Geopolitical Risk",
        "Social Sentiment",
        "News Sentiment",
        "Market Statistics",
        "Congress Trades",
        "Portfolio Risk",
    ]
    factor_chips = " ".join(
        f'<span class="badge badge-gray" style="margin:2px">{html.escape(f)}</span>'
        for f in factors
    )
    confidence_html = (
        '<div class="card">\n'
        "<h3>12-Factor Confidence Scoring</h3>\n"
        f"<p>{factor_chips}</p>\n"
        '<p style="margin-top:8px">'
        '<span class="badge badge-green">HIGH</span> 9+ favorable &bull; '
        '<span class="badge badge-yellow">MEDIUM</span> 5-8 &bull; '
        '<span class="badge badge-red">LOW</span> 0-4'
        "</p>\n</div>\n"
    )

    return (
        '<section id="about-strategy">\n'
        "<h2>Trading Strategy</h2>\n"
        + sector_table
        + lifecycle_html
        + confidence_html
        + "</section>\n"
    )


def _section_about_org_chart() -> str:
    """Render org chart as HTML/CSS layout."""
    # Board
    board = (
        '<div style="text-align:center;margin-bottom:24px">\n'
        '<div style="display:inline-block;padding:12px 24px;'
        "background:#1e293b;color:#f8fafc;border-radius:8px;"
        'font-weight:700;font-size:1.1em">'
        "Board of Directors (You)</div>\n"
        '<div style="width:2px;height:20px;background:#475569;'
        'margin:0 auto"></div>\n'
        "</div>\n"
    )

    # Executives
    executives = (
        '<div style="display:flex;justify-content:center;gap:24px;'
        'margin-bottom:24px;flex-wrap:wrap">\n'
        '<div style="padding:12px 20px;background:#1e3a5f;color:#f8fafc;'
        'border-radius:8px;text-align:center;min-width:200px">\n'
        '<div style="font-weight:700">CIO</div>'
        '<div style="font-size:0.85em;color:#94a3b8">'
        "exec-cio &bull; opus</div>\n"
        '<div style="font-size:0.8em;margin-top:4px">'
        "Cross-domain synthesis &amp; unified report</div>\n"
        "</div>\n"
        '<div style="padding:12px 20px;background:#1e3a5f;color:#f8fafc;'
        'border-radius:8px;text-align:center;min-width:200px">\n'
        '<div style="font-weight:700">COO</div>'
        '<div style="font-size:0.85em;color:#94a3b8">'
        "exec-coo &bull; haiku</div>\n"
        '<div style="font-size:0.8em;margin-top:4px">'
        "System health &amp; operations</div>\n"
        "</div>\n"
        "</div>\n"
    )

    # Departments
    departments = [
        (
            "Trading Desk",
            "#2563eb",
            [
                ("trading-drawdown-monitor", "Drawdown monitoring"),
                ("trading-market-analyst", "Momentum &amp; volatility"),
                ("trading-swing-screener", "Entry/exit signals"),
            ],
        ),
        (
            "Research",
            "#7c3aed",
            [
                ("research-macro", "Macro data (VIX, Fed, yields)"),
                ("research-sec", "SEC filings &amp; 13F"),
                ("research-statistics", "Sector rotation &amp; breadth"),
                ("research-strategy-analyst", "Backtesting &amp; optimization"),
                ("research-strategy-researcher", "New strategies (opus)"),
                ("research-quant", "Statistical analysis (opus)"),
            ],
        ),
        (
            "Intelligence",
            "#0891b2",
            [
                ("intel-chief", "Intel aggregation &amp; briefing"),
                ("intel-news", "Financial news sentiment"),
                ("intel-geopolitical", "GDELT &amp; geopolitical risk"),
                ("intel-social", "Reddit &amp; social sentiment"),
                ("intel-congress", "Congressional stock trades"),
            ],
        ),
        (
            "Risk Management",
            "#dc2626",
            [
                ("risk-manager", "Portfolio limits &amp; VETO authority"),
                ("risk-portfolio", "Position sizing &amp; allocations"),
            ],
        ),
        (
            "Operations",
            "#475569",
            [
                ("ops-code-reviewer", "Code quality (haiku)"),
                ("ops-design-reviewer", "UI/UX review"),
                ("ops-security-reviewer", "Security audit (haiku)"),
                ("ops-token-optimizer", "Token efficiency (haiku)"),
                ("ops-devops", "Pipeline health (haiku)"),
            ],
        ),
    ]

    dept_cards = ""
    for dept_name, color, agents in departments:
        agent_list = "".join(
            f'<div style="font-size:0.8em;padding:3px 0;'
            f'border-bottom:1px solid #1e293b">'
            f"<strong>{html.escape(name)}</strong> &mdash; {desc}</div>\n"
            for name, desc in agents
        )
        dept_cards += (
            f'<div style="flex:1;min-width:250px;border:2px solid {color};'
            f'border-radius:8px;overflow:hidden">\n'
            f'<div style="background:{color};color:#f8fafc;padding:8px 12px;'
            f'font-weight:700">{html.escape(dept_name)}'
            f'<span style="float:right;font-size:0.8em;opacity:0.8">'
            f"{len(agents)} agents</span></div>\n"
            f'<div style="padding:8px 12px">{agent_list}</div>\n'
            "</div>\n"
        )

    dept_html = (
        '<div style="display:flex;gap:16px;flex-wrap:wrap">\n' + dept_cards + "</div>\n"
    )

    return (
        '<section id="about-org">\n'
        "<h2>Organization</h2>\n"
        '<div class="card">\n' + board + executives + dept_html + "</div>\n</section>\n"
    )


def _section_about_data_sources() -> str:
    """Render data sources overview."""
    sources = [
        ("Yahoo Finance", "Stock prices, ATH, drawdown calculation"),
        ("FRED API", "VIX, CPI, GDP, unemployment, Fed funds rate"),
        ("SEC EDGAR", "10-K, 10-Q, 8-K filings, institutional 13F"),
        ("GDELT", "Global geopolitical events, conflict monitoring"),
        ("Congress.gov", "STOCK Act disclosures, member trading"),
        ("Reddit", "r/wallstreetbets, r/stocks sentiment"),
        ("Financial RSS", "Reuters, CNBC, AP Business news feeds"),
        ("Treasury.gov", "Yield curve rates across maturities"),
        ("Fed Reserve", "FOMC calendar, rate decisions, dot plot"),
        ("Geopolitical RSS", "Trade war, sanctions, territorial events"),
    ]

    items = ""
    for name, desc in sources:
        items += (
            f"<tr><td><strong>{html.escape(name)}</strong></td>"
            f"<td>{html.escape(desc)}</td></tr>\n"
        )

    return (
        '<section id="about-sources">\n'
        "<h2>Data Sources</h2>\n"
        '<div class="card">\n'
        "<table>\n<thead><tr>"
        "<th>Source</th><th>Data</th>"
        "</tr></thead>\n<tbody>\n" + items + "</tbody>\n</table>\n</div>\n</section>\n"
    )


def _section_about_schedule() -> str:
    """Render daily operational cadence."""
    return (
        '<section id="about-schedule">\n'
        "<h2>Daily Operations</h2>\n"
        '<div class="card">\n'
        '<div style="display:flex;gap:24px;flex-wrap:wrap">\n'
        # Pre-market
        '<div style="flex:1;min-width:280px">\n'
        '<h3 style="color:#2563eb">Pre-Market (7:00 AM ET)</h3>\n'
        "<ol>\n"
        "<li>Daily standup ceremony</li>\n"
        "<li>Data pipeline &mdash; 20+ modules (~2 min)</li>\n"
        "<li>HTML report published to GitHub Pages</li>\n"
        "<li>CIO synthesizes unified analysis</li>\n"
        "<li>Telegram alert with key signals</li>\n"
        "<li>Token usage &amp; pipeline health recorded</li>\n"
        "</ol>\n"
        '<p style="font-size:0.85em;color:#94a3b8">'
        "Monday: also runs sprint planning</p>\n"
        "</div>\n"
        # Post-market
        '<div style="flex:1;min-width:280px">\n'
        '<h3 style="color:#0a7c42">Post-Market (4:30 PM ET)</h3>\n'
        "<ol>\n"
        "<li>Data pipeline refresh with EOD data</li>\n"
        "<li>HTML report updated</li>\n"
        "<li>CIO reviews daily P&amp;L, signal state changes</li>\n"
        "<li>Overnight positioning &amp; catalysts</li>\n"
        "<li>Telegram summary</li>\n"
        "<li>Postmortem detection (Fridays)</li>\n"
        "</ol>\n"
        '<p style="font-size:0.85em;color:#94a3b8">'
        "Friday: also runs sprint retrospective</p>\n"
        "</div>\n"
        "</div>\n</div>\n</section>\n"
    )


def build_about_html(
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build about page with company overview, strategy, and team."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    hero = _section_about_hero()
    strategy = _section_about_strategy()
    org = _section_about_org_chart()
    sources = _section_about_data_sources()
    schedule = _section_about_schedule()

    top_bar = _page_header_bar(
        report_date, "about", report_dates, page_prefix="about-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "system overview &amp; methodology.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        hero,
        strategy,
        org,
        sources,
        schedule,
        "</main>\n",
        footer,
    ]

    return _html_page(
        title=f"About {report_date}",
        body="\n".join(p for p in body_parts if p),
        description="System overview, trading strategy, and team structure",
    )


# ---------------------------------------------------------------------------
# Roadmap page — quarterly OKRs, sprint timeline, progress tracking
# ---------------------------------------------------------------------------


def _section_roadmap_header() -> str:
    """Render the quarter header with overall progress."""
    roadmap = load_roadmap()
    if not roadmap.okrs:
        return ""
    total_pct = sum(o.progress_pct for o in roadmap.okrs) / len(roadmap.okrs)
    bar_cls = "green" if total_pct >= 66 else "yellow" if total_pct >= 33 else "red"
    return (
        "<section>\n"
        "<h2>Q1 2026 Roadmap &mdash; Feb 16 to May 15</h2>\n"
        '<div class="card">\n'
        f'<p><strong>Overall progress: {total_pct:.0f}%</strong></p>\n'
        f'<div class="progress-bar" style="height:8px">'
        f'<div class="progress-fill {bar_cls}" '
        f'style="width:{max(total_pct, 2):.0f}%"></div></div>\n'
        f"<p style=\"font-size:12px;color:var(--text-muted);margin-top:8px\">"
        f"{len(roadmap.okrs)} objectives &bull; "
        f"13 sprints (Sprint 4&ndash;17)</p>\n"
        "</div>\n</section>\n"
    )


def _section_sprint_timeline() -> str:
    """Render a horizontal sprint timeline for the quarter."""
    from app.agile.store import load_sprints

    sprints = load_sprints()
    # Quarter sprints: 4 through 17.
    quarter_sprints = [s for s in sprints if 4 <= s.number <= 17]

    cells: list[str] = []
    for i in range(4, 18):
        sp = next((s for s in quarter_sprints if s.number == i), None)
        if sp:
            st = sp.status.value if hasattr(sp.status, "value") else str(sp.status)
            if st == "ACTIVE":
                cls = "background:var(--accent);color:#fff"
            elif st == "COMPLETED":
                cls = "background:var(--success);color:#fff"
            else:
                cls = "background:var(--bg-secondary);color:var(--text-muted)"
            label = f"S{i}"
            tip = f"{sp.start_date}"
        else:
            cls = "background:var(--bg-secondary);color:var(--text-muted)"
            label = f"S{i}"
            tip = "planned"

        cells.append(
            f'<div style="display:inline-block;padding:4px 8px;margin:2px;'
            f"border-radius:4px;font-size:11px;font-family:var(--font-mono);"
            f'{cls}" title="{html.escape(tip)}">{label}</div>'
        )

    return (
        "<section>\n<h2>Sprint Timeline</h2>\n"
        '<div class="card">\n'
        '<div style="display:flex;flex-wrap:wrap;gap:2px">\n'
        + "\n".join(cells)
        + "\n</div>\n</div>\n</section>\n"
    )


def _section_roadmap_okrs() -> str:
    """Render detailed OKR cards with target sprint and status."""
    roadmap = load_roadmap()
    if not roadmap.okrs:
        return ""
    current = roadmap.current_sprint

    cards: list[str] = []
    for okr in roadmap.okrs:
        pct = okr.progress_pct
        bar_cls = "green" if pct >= 66 else "yellow" if pct >= 33 else "red"
        target = okr.target_sprint or 17

        # Status based on timeline progress.
        quarter_progress = max((current - 4) / 13 * 100, 0) if current >= 4 else 0
        if pct >= quarter_progress - 10:
            status_badge = '<span class="badge badge-green">On Track</span>'
        elif pct >= quarter_progress - 30:
            status_badge = '<span class="badge badge-yellow">At Risk</span>'
        else:
            status_badge = '<span class="badge badge-red">Behind</span>'

        kr_items = ""
        for kr in okr.key_results:
            kr_items += f"<li>{html.escape(kr)}</li>\n"

        cards.append(
            f'<div class="okr-card">\n'
            f"<h3>"
            f'<span class="okr-id">{html.escape(okr.id)}</span>'
            f"{html.escape(okr.objective)} "
            f"{status_badge}"
            f'<span class="okr-pct">{pct:.0f}%</span>'
            f"</h3>\n"
            f'<div class="progress-bar">'
            f'<div class="progress-fill {bar_cls}" '
            f'style="width:{max(pct, 2):.0f}%"></div></div>\n'
            f'<ul class="kr-list">{kr_items}</ul>\n'
            f'<p style="font-size:11px;color:var(--text-muted);margin-top:8px">'
            f"Target: Sprint {target}</p>\n"
            f"</div>\n",
        )

    body = "".join(cards)
    return (
        "<section>\n<h2>Objectives &amp; Key Results</h2>\n"
        f"{body}</section>\n"
    )


def _section_research_progress() -> str:
    """Render research document progress widget on roadmap page."""
    try:
        from app.research.store import list_documents

        docs = list_documents()
        complete = sum(1 for d in docs if d.status.value == "COMPLETE")
        in_prog = sum(1 for d in docs if d.status.value == "IN_PROGRESS")
        ideas = sum(1 for d in docs if d.status.value == "IDEA")
        total_target = 15

        pct = min(complete / total_target * 100, 100) if total_target else 0
        bar_cls = "green" if pct >= 66 else "yellow" if pct >= 33 else "red"

        return (
            "<section>\n<h2>Research Pipeline Progress</h2>\n"
            '<div class="card">\n'
            f"<p><strong>{complete}/{total_target}</strong> "
            f"research documents complete "
            f"&bull; {in_prog} in-progress &bull; {ideas} ideas</p>\n"
            f'<div class="progress-bar" style="height:8px">'
            f'<div class="progress-fill {bar_cls}" '
            f'style="width:{max(pct, 2):.0f}%"></div></div>\n'
            f"</div>\n</section>\n"
        )
    except Exception:
        return ""


def build_roadmap_html(
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build roadmap page with quarterly OKRs, sprint timeline, and progress."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    roadmap_header = _section_roadmap_header()
    timeline = _section_sprint_timeline()
    okrs = _section_roadmap_okrs()
    research_progress = _section_research_progress()

    top_bar = _page_header_bar(
        report_date, "roadmap", report_dates, page_prefix="roadmap-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "quarterly roadmap &amp; OKR tracking.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        roadmap_header,
        timeline,
        okrs,
        research_progress,
        "</main>\n",
        footer,
    ]

    return _html_page(
        title=f"Roadmap {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"Q1 2026 quarterly roadmap and OKR progress for {report_date}",
    )


# ---------------------------------------------------------------------------
# Research page — research document library
# ---------------------------------------------------------------------------


_STATUS_COLORS: dict[str, str] = {
    "IDEA": "var(--text-muted)",
    "IN_PROGRESS": "var(--accent)",
    "DRAFT": "var(--warning)",
    "COMPLETE": "var(--success)",
    "ARCHIVED": "var(--text-muted)",
}

_TYPE_LABELS: dict[str, str] = {
    "NEW_STRATEGY": "New Strategy",
    "NEW_ETF": "New ETF",
    "MARKET_ANOMALY": "Market Anomaly",
    "RISK_MANAGEMENT": "Risk Management",
}


def _section_research_status() -> str:
    """Render research pipeline status header."""
    try:
        from app.research.store import get_sprint_progress, list_documents, load_state

        state = load_state()
        docs = list_documents()
        completed, target = get_sprint_progress(state.current_sprint)
        in_prog = sum(1 for d in docs if d.status.value == "IN_PROGRESS")
        ideas = sum(1 for d in docs if d.status.value == "IDEA")
        total_complete = sum(1 for d in docs if d.status.value == "COMPLETE")

        pct = min(completed / target * 100, 100) if target else 0
        bar_cls = "green" if pct >= 66 else "yellow" if pct >= 33 else "red"

        return (
            "<section>\n<h2>Research Pipeline</h2>\n"
            '<div class="card">\n'
            f"<p><strong>{total_complete}</strong> complete &bull; "
            f"<strong>{in_prog}</strong> in-progress &bull; "
            f"<strong>{ideas}</strong> ideas &bull; "
            f"Sprint {state.current_sprint} target: "
            f"<strong>{completed}/{target}</strong></p>\n"
            f'<div class="progress-bar" style="height:6px;margin-top:8px">'
            f'<div class="progress-fill {bar_cls}" '
            f'style="width:{max(pct, 2):.0f}%"></div></div>\n'
            f"</div>\n</section>\n"
        )
    except Exception:
        return (
            "<section>\n<h2>Research Pipeline</h2>\n"
            '<div class="card"><p class="text-muted">'
            "No research data available</p></div>\n</section>\n"
        )


def _render_section_dots(doc: object) -> str:
    """Render 9 section progress dots for a research document."""
    dots: list[str] = []
    sections = getattr(doc, "sections", [])
    for s in sections:
        status = s.status.value if hasattr(s.status, "value") else str(s.status)
        if status == "COMPLETE":
            color = "var(--success)"
        elif status == "DRAFT":
            color = "var(--warning)"
        else:
            color = "var(--bg-dark)"
        tip = html.escape(f"{s.title}: {status}")
        dots.append(
            f'<span style="display:inline-block;width:10px;height:10px;'
            f"border-radius:50%;background:{color};margin-right:3px;"
            f'border:1px solid var(--border-light)" title="{tip}"></span>'
        )
    return "".join(dots)


def _hypothesis_html(hypothesis: str) -> str:
    """Render hypothesis paragraph if present."""
    if not hypothesis:
        return ""
    escaped = html.escape(hypothesis[:200])
    return (
        '<p style="font-size:12px;color:var(--text-secondary);'
        f'margin-top:4px;font-style:italic">{escaped}</p>'
    )


def _doc_body(section_html: str) -> str:
    """Return section HTML or a placeholder."""
    if section_html:
        return section_html
    return '<p class="text-muted">No content yet</p>'


def _render_document_card(doc: object) -> str:
    """Render a single research document card."""
    doc_id = getattr(doc, "id", "?")
    title = getattr(doc, "title", "Untitled")
    status = getattr(doc, "status", "")
    status_val = status.value if hasattr(status, "value") else str(status)
    rt = getattr(doc, "research_type", "")
    type_val = rt.value if hasattr(rt, "value") else str(rt)
    priority = getattr(doc, "priority", "MEDIUM")
    sprint = getattr(doc, "sprint_number", 0)
    updated = getattr(doc, "updated_date", "")[:10]
    hypothesis = getattr(doc, "hypothesis", "")
    tags = getattr(doc, "tags", [])

    status_color = _STATUS_COLORS.get(status_val, "var(--text-muted)")
    type_label = _TYPE_LABELS.get(type_val, type_val)

    # Section progress.
    sections = getattr(doc, "sections", [])
    filled = sum(1 for s in sections if s.status.value != "EMPTY")
    complete = sum(1 for s in sections if s.status.value == "COMPLETE")

    dots = _render_section_dots(doc)
    tag_badges = " ".join(
        f'<span class="sector-badge">{html.escape(t)}</span>' for t in tags[:5]
    )

    # Build section content for expandable view.
    section_html = ""
    for s in sections:
        s_status = s.status.value if hasattr(s.status, "value") else str(s.status)
        if s.content:
            # Simple markdown-to-HTML: paragraphs and code blocks.
            content_escaped = html.escape(s.content)
            content_formatted = content_escaped.replace(
                "\n\n", "</p><p>",
            ).replace("\n", "<br>")
            section_html += (
                f'<div style="margin-bottom:16px">'
                f'<h4 style="font-size:13px;'
                f'color:var(--text-primary);margin-bottom:4px">'
                f'{html.escape(s.title)} '
                f'<span style="font-size:11px;'
                f'color:{_STATUS_COLORS.get(s_status, "var(--text-muted)")}">'
                f'[{s_status}]</span></h4>'
                f'<div style="font-size:13px;color:var(--text-secondary);'
                f'line-height:1.6"><p>{content_formatted}</p></div>'
                f"</div>"
            )
        elif s_status != "EMPTY":
            section_html += (
                f'<div style="margin-bottom:8px">'
                f'<h4 style="font-size:13px;color:var(--text-muted)">'
                f"{html.escape(s.title)} [{s_status}]</h4>"
                f"</div>"
            )

    expanded = status_val == "COMPLETE"
    prio_cls = {
        "HIGH": "red", "MEDIUM": "yellow",
    }.get(priority, "green")
    meta = f"S{sprint} &bull; {html.escape(updated)}"
    open_attr = ' open' if expanded else ''
    id_span = (
        f'<span style="font-family:var(--font-mono);'
        f'font-size:12px;color:var(--text-muted)">'
        f"{html.escape(doc_id)}</span>"
    )
    progress_span = (
        f'<span style="font-size:11px;'
        f'color:var(--text-muted)">'
        f"{complete}/{filled}/9</span>"
    )
    summary_style = (
        "font-size:12px;color:var(--accent);"
        "cursor:pointer;margin-top:8px"
    )

    return (
        f'<div class="card" style="margin-bottom:12px">\n'
        f'<div style="display:flex;'
        f'justify-content:space-between;'
        f'align-items:center">\n'
        f"<div>\n"
        f"{id_span}\n"
        f'<strong style="margin-left:8px">'
        f"{html.escape(title)}</strong>\n"
        f'<span class="badge" style="'
        f"background:{status_color};color:#fff;"
        f'margin-left:8px">{status_val}</span>\n'
        f'<span class="sector-badge"'
        f' style="margin-left:4px">'
        f"{html.escape(type_label)}</span>\n"
        f'<span class="badge badge-{prio_cls}"'
        f' style="margin-left:4px">'
        f"{html.escape(priority)}</span>\n"
        f"</div>\n"
        f'<div style="font-size:11px;'
        f'color:var(--text-muted)">{meta}</div>\n'
        f"</div>\n"
        f'<div style="margin:8px 0">{dots} '
        f"{progress_span}</div>\n"
        f'{f"<div>{tag_badges}</div>" if tag_badges else ""}'
        f"{_hypothesis_html(hypothesis)}\n"
        f"<details{open_attr}>\n"
        f'<summary style="{summary_style}">'
        f"View full document</summary>\n"
        f'<div style="padding:12px 0">'
        f"{_doc_body(section_html)}"
        f"</div>\n</details>\n"
        f"</div>\n"
    )


def _section_research_documents() -> str:
    """Render all research documents as cards."""
    try:
        from app.research.models import DocumentStatus
        from app.research.store import list_documents

        docs = list_documents()
        if not docs:
            return (
                "<section>\n<h2>Research Documents</h2>\n"
                '<div class="card"><p class="text-muted">'
                "No research documents yet. The researcher will create "
                "documents during scheduled runs.</p></div>\n</section>\n"
            )

        # Sort: COMPLETE first, then IN_PROGRESS, then DRAFT, then IDEA.
        order = {
            DocumentStatus.COMPLETE: 0,
            DocumentStatus.DRAFT: 1,
            DocumentStatus.IN_PROGRESS: 2,
            DocumentStatus.IDEA: 3,
            DocumentStatus.ARCHIVED: 4,
        }
        docs.sort(key=lambda d: (order.get(d.status, 9), d.id))

        cards = "".join(_render_document_card(d) for d in docs)
        n = len(docs)
        return (
            f"<section>\n<h2>Research Documents ({n})"
            f"</h2>\n{cards}</section>\n"
        )
    except Exception:
        return ""


def build_research_html(
    *,
    date: str = "",
    report_dates: list[str] | None = None,
) -> str:
    """Build research documents page with document library and progress."""
    report_date = date or datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    report_time = datetime.now(tz=_ISRAEL_TZ).strftime("%H:%M IST")

    status = _section_research_status()
    documents = _section_research_documents()

    top_bar = _page_header_bar(
        report_date, "research", report_dates, page_prefix="research-",
    )

    header = (
        '<header class="header">\n'
        f"<span>{html.escape(report_date)} &bull; "
        f"{html.escape(report_time)}</span>\n"
        "</header>\n"
    )

    footer = (
        '<footer class="footer">\n'
        f"<span>Generated {html.escape(report_date)} "
        f"{html.escape(report_time)} &mdash; "
        "strategy research document library.</span>\n"
        "</footer>\n"
    )

    body_parts = [
        top_bar,
        header,
        '<main id="main-content">\n',
        status,
        documents,
        "</main>\n",
        footer,
    ]

    return _html_page(
        title=f"Research {report_date}",
        body="\n".join(p for p in body_parts if p),
        description=f"Strategy research documents for {report_date}",
    )

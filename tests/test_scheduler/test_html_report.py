from __future__ import annotations

import json
import subprocess as sp
from pathlib import Path
from unittest.mock import patch

from app.scheduler.html_report import (
    build_forecasts_html,
    build_html_report,
    build_index_html,
    build_trade_logs_html,
)
from app.scheduler.publisher import (
    _discover_report_dates,
    git_publish,
    write_report,
)
from app.scheduler.runner import ModuleResult, SchedulerRun


def _make_run(
    results: list[ModuleResult] | None = None,
) -> SchedulerRun:
    r = results or []
    succeeded = sum(1 for x in r if x.success)
    return SchedulerRun(
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:01:00+00:00",
        results=r,
        total_modules=len(r),
        succeeded=succeeded,
        failed=len(r) - succeeded,
    )


def _ok(name: str, output: str = "") -> ModuleResult:
    return ModuleResult(
        name=name,
        success=True,
        output=output,
        error="",
        duration_seconds=1.0,
    )


def _fail(name: str) -> ModuleResult:
    return ModuleResult(
        name=name,
        success=False,
        output="",
        error="some error",
        duration_seconds=1.0,
    )


# --- HTML generation tests ---


def test_build_html_report_empty_run():
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "<!DOCTYPE html>" in html
    assert "2026-01-15" in html
    assert "not financial advice" in html


def test_build_html_report_has_dashboard_css():
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "<style>" in html
    assert "kpi-strip" in html
    assert "kpi-card" in html
    assert "grid-2col" in html
    assert "module-grid" in html
    assert "module-pill" in html


def test_build_html_report_header():
    run = _make_run([_ok("etf.signals", "[]"), _fail("macro.dashboard")])
    html = build_html_report(run, date="2026-01-15")
    assert "Dashboard" in html
    assert ">1</span>/2 OK" in html
    assert ">1</span> failed" in html
    assert "top-bar" in html


def test_build_html_report_kpi_vix():
    data = json.dumps(
        {
            "vix": 22.5,
            "vix_regime": "ELEVATED",
        }
    )
    run = _make_run([_ok("macro.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "22.5" in html
    assert "ELEVATED" in html
    assert "kpi-card" in html
    assert "kpi-bar-red" in html  # ELEVATED -> red


def test_build_html_report_kpi_fed_from_rates():
    """Fed trajectory comes from macro.rates, not macro.dashboard."""
    macro = json.dumps({"vix": 15.0, "vix_regime": "NORMAL"})
    rates = json.dumps(
        {
            "trajectory": "HIKING",
            "current_rate": 5.25,
        }
    )
    run = _make_run(
        [
            _ok("macro.dashboard", macro),
            _ok("macro.rates", rates),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    assert "5.25%" in html
    assert "HIKING" in html


def test_build_html_report_kpi_yields():
    data = json.dumps(
        {
            "curve_status": "INVERTED",
            "spread_3m_10y": -0.42,
        }
    )
    run = _make_run([_ok("macro.yields", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "INVERTED" in html
    assert "-0.42%" in html
    assert "kpi-bar-red" in html


def test_build_html_report_kpi_geopolitical():
    data = json.dumps({"risk_level": "HIGH", "total_events": 5})
    run = _make_run([_ok("geopolitical.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "HIGH" in html
    assert "5 events" in html


def test_build_html_report_kpi_news():
    data = json.dumps(
        {
            "sentiment": "BEARISH",
            "total_articles": 42,
        }
    )
    run = _make_run([_ok("news.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "BEARISH" in html
    assert "42 articles" in html


def test_build_html_report_kpi_strip_all_sources():
    run = _make_run(
        [
            _ok(
                "macro.dashboard",
                json.dumps(
                    {
                        "vix": 18.5,
                        "vix_regime": "NORMAL",
                    }
                ),
            ),
            _ok(
                "macro.rates",
                json.dumps(
                    {
                        "trajectory": "CUTTING",
                        "current_rate": 4.50,
                    }
                ),
            ),
            _ok(
                "macro.yields",
                json.dumps(
                    {
                        "curve_status": "NORMAL",
                        "spread_3m_10y": 0.35,
                    }
                ),
            ),
            _ok(
                "geopolitical.summary",
                json.dumps(
                    {
                        "risk_level": "LOW",
                        "total_events": 1,
                    }
                ),
            ),
            _ok(
                "news.summary",
                json.dumps(
                    {
                        "sentiment": "BULLISH",
                        "total_articles": 99,
                    }
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    # 5 KPI cards: VIX, Fed, Yield, Geo, News
    assert html.count("kpi-card") >= 5
    assert "kpi-strip" in html


def test_build_html_report_gauge_bars():
    """KPI cards include gauge bars for VIX and yields."""
    run = _make_run(
        [
            _ok(
                "macro.dashboard",
                json.dumps(
                    {
                        "vix": 25.0,
                        "vix_regime": "ELEVATED",
                    }
                ),
            ),
            _ok(
                "macro.yields",
                json.dumps(
                    {
                        "curve_status": "NORMAL",
                        "spread_3m_10y": 0.5,
                    }
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    assert "gauge-track" in html
    assert "gauge-fill" in html


def test_build_html_report_exec_summary_no_signals():
    """Exec summary shown even with no signals."""
    run = _make_run(
        [
            _ok(
                "macro.dashboard",
                json.dumps(
                    {
                        "vix": 15.0,
                        "vix_regime": "NORMAL",
                    }
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    assert "exec-summary" in html
    assert "No actionable signals" in html


def test_build_html_report_exec_summary_with_signals():
    """Exec summary shows confidence and stance when signals exist."""
    run = _make_run(
        [
            _ok(
                "etf.signals",
                json.dumps(
                    [
                        {
                            "leveraged_ticker": "TQQQ",
                            "underlying_ticker": "QQQ",
                            "state": "SIGNAL",
                            "underlying_drawdown_pct": -0.12,
                            "underlying_ath": 520.0,
                            "underlying_current": 457.6,
                        }
                    ]
                ),
            ),
            _ok(
                "macro.dashboard",
                json.dumps(
                    {
                        "vix": 25.0,
                        "vix_regime": "ELEVATED",
                    }
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    assert "exec-summary" in html
    assert "SIGNAL" in html
    assert "confidence" in html.lower()


def test_build_html_report_signal_cards():
    """ETF signals rendered as individual cards with confidence."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "state": "SIGNAL",
                "underlying_drawdown_pct": -0.072,
                "underlying_ath": 520.0,
                "underlying_current": 482.56,
            }
        ]
    )
    run = _make_run([_ok("etf.signals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "TQQQ" in html
    assert "QQQ" in html
    assert "SIGNAL" in html
    assert "$520.00" in html
    assert "$482.56" in html
    assert "signal-card" in html
    assert "confidence-bar" in html


def test_build_html_report_signal_confidence_drilldown():
    """Signal cards have details/summary for 9-factor analysis."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "state": "SIGNAL",
                "underlying_drawdown_pct": -0.072,
            }
        ]
    )
    run = _make_run([_ok("etf.signals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "<details>" in html
    assert "9-factor analysis" in html
    assert "factor-table" in html


def test_build_html_report_signal_with_pl():
    data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "state": "ACTIVE",
                "underlying_drawdown_pct": -0.05,
                "current_pl_pct": 0.08,
            }
        ]
    )
    run = _make_run([_ok("etf.signals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "pct-up" in html
    assert "+8.0%" in html


def test_build_html_report_sentiment_section():
    """Sentiment section shows bars and counts."""
    data = json.dumps(
        {
            "sentiment": "BEARISH",
            "total_articles": 100,
            "bullish_count": 20,
            "bearish_count": 50,
            "neutral_count": 30,
        }
    )
    run = _make_run([_ok("news.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "Sentiment Analysis" in html
    assert "sentiment-bar" in html
    assert "sentiment-fill-bullish" in html
    assert "sentiment-fill-bearish" in html
    assert "20 bullish" in html
    assert "50 bearish" in html
    assert "30 neutral" in html


def test_build_html_report_sentiment_headlines():
    """Sentiment section has expandable headlines."""
    data = json.dumps(
        {
            "sentiment": "BULLISH",
            "total_articles": 10,
            "bullish_count": 7,
            "bearish_count": 2,
            "neutral_count": 1,
            "top_headlines": [
                {"title": "Markets rally", "sentiment": "BULLISH"},
            ],
        }
    )
    run = _make_run([_ok("news.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "Top headlines" in html
    assert "Markets rally" in html


def test_build_html_report_sentiment_sectors():
    """Sentiment section shows sector badges."""
    data = json.dumps(
        {
            "sentiment": "NEUTRAL",
            "total_articles": 50,
            "bullish_count": 15,
            "bearish_count": 15,
            "neutral_count": 20,
            "sector_mentions": {"technology": 25, "energy": 10},
        }
    )
    run = _make_run([_ok("news.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "sector-badge" in html
    assert "technology" in html


def test_build_html_report_officials_tone():
    """Social officials shown in sentiment section with correct field."""
    run = _make_run(
        [
            _ok(
                "social.summary",
                json.dumps(
                    {
                        "officials": {
                            "fed_tone": "HAWKISH",
                            "policy_direction": "CONTRACTIONARY",
                        },
                    }
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    assert "HAWKISH" in html
    assert "CONTRACTIONARY" in html


def test_build_html_report_strategy():
    data = json.dumps(
        [
            {
                "leveraged_ticker": "SOXL",
                "improvement_reason": "Better Sharpe at 10%",
                "backtest_sharpe": 2.15,
                "backtest_win_rate": 0.75,
                "backtest_total_return": 0.42,
            }
        ]
    )
    run = _make_run([_ok("strategy.proposals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "SOXL" in html
    assert "Better Sharpe" in html
    assert "2.15" in html
    assert "75.0%" in html
    assert "+42.0%" in html


def test_build_html_report_market_conditions():
    data = json.dumps(
        {
            "risk_indicators": {
                "risk_assessment": "RISK_OFF",
                "gold_price": 2050.5,
                "gold_change_5d_pct": 0.023,
                "oil_price": 78.2,
                "oil_change_5d_pct": -0.015,
                "dxy_price": 104.3,
                "dxy_change_5d_pct": 0.005,
            },
            "correlations": {
                "decoupled_pairs": ["SPY-IWM"],
            },
        }
    )
    run = _make_run([_ok("statistics.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "RISK_OFF" in html
    assert "Gold" in html
    assert "$2,050.50" in html
    assert "Oil" in html
    assert "DXY" in html
    assert "DECOUPLING" in html
    assert "SPY-IWM" in html


def test_build_html_report_module_status_pills():
    run = _make_run([_ok("etf.signals", "[]"), _fail("macro.dashboard")])
    html = build_html_report(run, date="2026-01-15")
    assert "module-grid" in html
    assert "module-pill-ok" in html
    assert "module-pill-fail" in html
    assert "etf.signals" in html
    assert "macro.dashboard" in html


def test_build_html_report_xss_safety():
    data = json.dumps(
        {
            "vix": 20.0,
            "vix_regime": "<script>alert('xss')</script>",
        }
    )
    run = _make_run([_ok("macro.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_build_html_report_two_col_grid():
    """Grid used when both sentiment and conditions present."""
    run = _make_run(
        [
            _ok(
                "news.summary",
                json.dumps(
                    {
                        "sentiment": "BEARISH",
                        "total_articles": 10,
                        "bullish_count": 2,
                        "bearish_count": 6,
                        "neutral_count": 2,
                    }
                ),
            ),
            _ok(
                "statistics.dashboard",
                json.dumps(
                    {
                        "risk_indicators": {"risk_assessment": "NEUTRAL"},
                    }
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    assert "grid-2col" in html


def test_build_html_report_responsive():
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "@media" in html
    assert "900px" in html


def test_build_html_report_all_sections():
    run = _make_run(
        [
            _ok(
                "macro.dashboard",
                json.dumps(
                    {
                        "vix": 12.0,
                        "vix_regime": "CALM",
                    }
                ),
            ),
            _ok(
                "macro.rates",
                json.dumps(
                    {
                        "trajectory": "HOLDING",
                        "current_rate": 4.50,
                    }
                ),
            ),
            _ok(
                "macro.yields",
                json.dumps(
                    {
                        "curve_status": "NORMAL",
                        "spread_3m_10y": 0.5,
                    }
                ),
            ),
            _ok(
                "geopolitical.summary",
                json.dumps(
                    {
                        "risk_level": "LOW",
                        "total_events": 2,
                    }
                ),
            ),
            _ok(
                "social.summary",
                json.dumps(
                    {
                        "officials": {"fed_tone": "NEUTRAL"},
                    }
                ),
            ),
            _ok(
                "news.summary",
                json.dumps(
                    {
                        "sentiment": "BULLISH",
                        "total_articles": 30,
                        "bullish_count": 20,
                        "bearish_count": 5,
                        "neutral_count": 5,
                    }
                ),
            ),
            _ok(
                "statistics.dashboard",
                json.dumps(
                    {
                        "risk_indicators": {"risk_assessment": "LOW"},
                    }
                ),
            ),
            _ok(
                "etf.signals",
                json.dumps(
                    [
                        {
                            "leveraged_ticker": "TQQQ",
                            "underlying_ticker": "QQQ",
                            "state": "WATCH",
                            "underlying_drawdown_pct": -0.03,
                        }
                    ]
                ),
            ),
            _ok(
                "strategy.proposals",
                json.dumps(
                    [
                        {
                            "leveraged_ticker": "SOXL",
                            "improvement_reason": "Good entry",
                        }
                    ]
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-02-01")
    assert "CALM" in html
    assert "TQQQ" in html
    assert "SOXL" in html
    assert "All Reports" in html
    assert "exec-summary" in html
    assert "kpi-strip" in html
    assert "grid-2col" in html
    assert "module-grid" in html
    assert "signal-card" in html


# --- New feature tests ---


def test_build_html_report_material_icons_font():
    """Google Material Symbols font is loaded."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "Material+Symbols+Outlined" in html
    assert "material-symbols-outlined" in html


def test_build_html_report_fluid_layout():
    """Report uses fluid layout without fixed max-width."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "width: 100%" in html
    assert "clamp(16px" in html


def test_build_html_report_signal_grid():
    """Signal cards are rendered in a CSS grid."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "state": "SIGNAL",
                "underlying_drawdown_pct": -0.072,
            },
            {
                "leveraged_ticker": "SOXL",
                "underlying_ticker": "SOXX",
                "state": "ALERT",
                "underlying_drawdown_pct": -0.05,
            },
        ]
    )
    run = _make_run([_ok("etf.signals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "signal-grid" in html
    assert "TQQQ" in html
    assert "SOXL" in html


def test_build_html_report_index_tiles():
    """Market conditions section shows major index tiles."""
    data = json.dumps(
        {
            "risk_indicators": {
                "risk_assessment": "NEUTRAL",
                "spy_price": 545.20,
                "spy_change_1d_pct": 0.012,
                "qqq_price": 480.50,
                "qqq_change_1d_pct": -0.005,
                "dia_price": 420.00,
                "dia_change_1d_pct": 0.003,
            },
        }
    )
    run = _make_run([_ok("statistics.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "index-tile" in html
    assert "S&amp;P 500" in html or "S&P 500" in html
    assert "NASDAQ" in html
    assert "DOW" in html
    assert "$545.20" in html
    assert "$480.50" in html
    assert "$420.00" in html
    assert "+1.2%" in html
    assert "pct-up" in html
    assert "pct-down" in html


def test_build_html_report_global_rates():
    """Market conditions section shows global central bank rates."""
    rates = json.dumps(
        {
            "trajectory": "HOLDING",
            "current_rate": 4.50,
            "global_rates": {
                "ecb": 3.75,
                "boe": 4.25,
                "boj": 0.10,
            },
        }
    )
    run = _make_run([_ok("macro.rates", rates)])
    html = build_html_report(run, date="2026-01-15")
    assert "rates-grid" in html
    assert "rate-tile" in html
    assert "ECB" in html
    assert "BOE" in html
    assert "BOJ" in html
    assert "3.75%" in html
    assert "4.25%" in html
    assert "0.10%" in html


def test_build_html_report_headline_links():
    """News headlines include clickable links and sources."""
    data = json.dumps(
        {
            "sentiment": "BULLISH",
            "total_articles": 10,
            "bullish_count": 7,
            "bearish_count": 2,
            "neutral_count": 1,
            "top_headlines": [
                {
                    "title": "Markets rally hard",
                    "link": "https://example.com/article1",
                    "source": "Reuters",
                    "sentiment": "BULLISH",
                },
            ],
        }
    )
    run = _make_run([_ok("news.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert 'href="https://example.com/article1"' in html
    assert 'target="_blank"' in html
    assert "Reuters" in html
    assert "hl-source" in html


def test_build_html_report_geopolitical_event_links():
    """Geopolitical events include clickable links."""
    data = json.dumps(
        {
            "risk_level": "MEDIUM",
            "total_events": 3,
            "high_impact_count": 1,
            "top_events": [
                {
                    "title": "Trade tensions escalate",
                    "url": "https://example.com/geo1",
                    "category": "trade",
                    "impact": "HIGH",
                    "sectors": ["technology"],
                },
            ],
        }
    )
    run = _make_run([_ok("geopolitical.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert 'href="https://example.com/geo1"' in html
    assert "Trade tensions escalate" in html
    assert "technology" in html
    assert "geo-event" in html


def test_build_html_report_strategy_detail_columns():
    """Strategy table has Trades and Max DD columns."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "SOXL",
                "improvement_reason": "Better Sharpe",
                "backtest_sharpe": 1.80,
                "backtest_win_rate": 0.70,
                "backtest_total_return": 0.35,
                "backtest_trade_count": 12,
                "backtest_max_drawdown": -0.18,
                "backtest_period": "2y",
                "backtest_avg_gain": 0.12,
                "backtest_avg_loss": -0.06,
            }
        ]
    )
    run = _make_run([_ok("strategy.proposals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "Trades" in html
    assert "Max DD" in html
    assert "12" in html
    assert "-18.0%" in html
    assert "2y" in html
    assert "Sharpe ratio" in html
    assert "avg gain" in html
    assert "avg loss" in html


def test_build_html_report_strategy_low_trade_count_warning():
    """Strategy table warns when trade count is low."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "SOXL",
                "improvement_reason": "Test entry",
                "backtest_sharpe": 1.0,
                "backtest_win_rate": 0.5,
                "backtest_total_return": 0.1,
                "backtest_trade_count": 3,
            }
        ]
    )
    run = _make_run([_ok("strategy.proposals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "trade-count-warn" in html


def test_build_html_report_strategy_entry_exit_details():
    """Strategy table shows entry/exit strategy and avg hold duration."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "SOXL",
                "strategy_type": "rsi_oversold",
                "strategy_description": "Buy when RSI(14) drops below threshold",
                "threshold_label": "RSI level",
                "improvement_reason": "Better Sharpe",
                "backtest_sharpe": 1.80,
                "backtest_win_rate": 0.70,
                "backtest_total_return": 0.35,
                "backtest_trade_count": 12,
                "backtest_max_drawdown": -0.18,
                "backtest_total_days": 480,
                "proposed_threshold": 30.0,
                "current_threshold": 0.05,
                "proposed_target": 0.15,
                "current_target": 0.10,
            }
        ]
    )
    run = _make_run([_ok("strategy.proposals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "Avg Hold" in html
    assert "~40d" in html  # 480 / 12 = 40 days
    assert "strategy-entry-exit" in html
    assert "RSI level" in html
    assert "RSI" in html
    assert "+15% profit target" in html
    assert "current: +10%" in html


def test_build_html_report_nav_menu():
    """Report includes unified nav with cross-page and section links."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "nav-menu" in html
    # Cross-page links
    assert "2026-01-15.html" in html
    assert "trade-logs-2026-01-15.html" in html
    assert "forecasts-2026-01-15.html" in html
    assert "../index.html" in html
    # Dashboard should be active
    assert "nav-active" in html
    # Section anchors (only on dashboard)
    assert 'href="#signals"' in html
    assert 'href="#sentiment"' in html
    assert 'href="#market"' in html
    assert 'href="#geopolitical"' in html
    assert 'href="#strategy"' in html
    assert 'href="#research"' in html
    assert 'href="#modules"' in html
    assert 'aria-label="Report navigation"' in html


def test_build_html_report_section_ids():
    """All major sections have anchor IDs for navigation."""
    run = _make_run(
        [
            _ok(
                "etf.signals",
                json.dumps(
                    [
                        {
                            "leveraged_ticker": "TQQQ",
                            "underlying_ticker": "QQQ",
                            "state": "WATCH",
                            "underlying_drawdown_pct": -0.03,
                        }
                    ]
                ),
            ),
            _ok(
                "news.summary",
                json.dumps(
                    {
                        "sentiment": "BULLISH",
                        "total_articles": 10,
                        "bullish_count": 7,
                        "bearish_count": 2,
                        "neutral_count": 1,
                    }
                ),
            ),
            _ok(
                "statistics.dashboard",
                json.dumps(
                    {"risk_indicators": {"risk_assessment": "LOW"}},
                ),
            ),
            _ok(
                "geopolitical.summary",
                json.dumps(
                    {"risk_level": "LOW", "total_events": 1},
                ),
            ),
            _ok(
                "strategy.proposals",
                json.dumps(
                    [
                        {
                            "leveraged_ticker": "SOXL",
                            "improvement_reason": "Good",
                            "proposed_threshold": 0.10,
                            "proposed_target": 0.15,
                        }
                    ]
                ),
            ),
        ]
    )
    html = build_html_report(run, date="2026-01-15")
    assert 'id="signals"' in html
    assert 'id="sentiment"' in html
    assert 'id="market"' in html
    assert 'id="geopolitical"' in html
    assert 'id="strategy"' in html
    assert 'id="research"' in html
    assert 'id="modules"' in html


def test_build_html_report_strategy_research_section():
    """Strategy research section summarizes optimization exploration."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "SOXL",
                "improvement_reason": "Better Sharpe",
                "proposed_threshold": 0.10,
                "proposed_target": 0.15,
            },
            {
                "leveraged_ticker": "TQQQ",
                "improvement_reason": "Lower DD",
                "proposed_threshold": 0.07,
                "proposed_target": 0.10,
            },
        ]
    )
    run = _make_run([_ok("strategy.proposals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "Strategy Research" in html
    assert "2 ETF(s)" in html
    assert "SOXL" in html
    assert "TQQQ" in html
    assert "sector-badge" in html


def test_build_html_report_israel_timezone():
    """Report header shows IST timezone indicator."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "IST" in html


def test_build_html_report_modern_card_style():
    """Cards use modern styling with shadows and rounded corners."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "border-radius: 8px" in html
    assert "box-shadow" in html


# --- Index tests ---


def test_build_index_html_empty():
    html = build_index_html([])
    assert "<!DOCTYPE html>" in html
    assert "0 report(s)" in html


def test_build_index_html_with_dates():
    html = build_index_html(["2026-01-15", "2026-01-14"])
    assert "2 report(s)" in html
    assert 'href="reports/2026-01-15.html"' in html
    assert "2026-01-14" in html


def test_build_index_html_order():
    html = build_index_html(["2026-01-15", "2026-01-14"])
    pos_15 = html.index("2026-01-15")
    pos_14 = html.index("2026-01-14")
    assert pos_15 < pos_14


def test_build_index_html_latest_badge():
    html = build_index_html(["2026-01-15", "2026-01-14"])
    assert "LATEST" in html
    latest_pos = html.index("LATEST")
    pos_15 = html.index("2026-01-15")
    assert latest_pos > pos_15  # LATEST appears after first date


def test_build_index_html_report_cards():
    html = build_index_html(["2026-01-15"])
    assert "report-card" in html
    assert "report-list" in html


# --- File writing tests ---


def test_write_report_creates_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR",
        tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    run = _make_run([_ok("etf.signals", "[]")])
    path = write_report(run, date="2026-01-15")

    assert path.exists()
    assert path.name == "2026-01-15.html"
    assert (tmp_path / "docs" / "index.html").exists()


def test_write_report_index_includes_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR",
        tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    run = _make_run()
    write_report(run, date="2026-01-14")
    write_report(run, date="2026-01-15")

    index = (tmp_path / "docs" / "index.html").read_text()
    assert "2026-01-14" in index
    assert "2026-01-15" in index


def test_write_report_overwrites_same_date(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR",
        tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    run1 = _make_run([_ok("etf.signals", "[]")])
    run2 = _make_run(
        [
            _ok(
                "macro.dashboard",
                json.dumps(
                    {
                        "vix": 30.0,
                        "vix_regime": "HIGH",
                    }
                ),
            )
        ]
    )
    write_report(run1, date="2026-01-15")
    write_report(run2, date="2026-01-15")

    content = (tmp_path / "docs" / "reports" / "2026-01-15.html").read_text()
    assert "HIGH" in content


def test_discover_report_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path,
    )
    (tmp_path / "2026-01-13.html").write_text("<html></html>")
    (tmp_path / "2026-01-15.html").write_text("<html></html>")
    (tmp_path / "2026-01-14.html").write_text("<html></html>")
    (tmp_path / "not-a-date.html").write_text("<html></html>")

    dates = _discover_report_dates()
    assert dates == ["2026-01-15", "2026-01-14", "2026-01-13"]


def test_nojekyll_created(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR",
        tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    write_report(_make_run(), date="2026-01-15")
    assert (tmp_path / "docs" / ".nojekyll").exists()


# --- Trade logs page tests ---


def test_build_trade_logs_html_with_data():
    """Trade logs page generates with equity chart and trade table."""
    backtest_data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "leverage": 3.0,
                "entry_threshold": 0.05,
                "profit_target": 0.10,
                "period": "2y",
                "total_days": 500,
                "total_return": 0.35,
                "sharpe_ratio": 1.5,
                "win_rate": 0.7,
                "max_drawdown": 0.12,
                "avg_gain": 0.08,
                "avg_loss": -0.04,
                "trade_count": 5,
                "trades": [
                    {
                        "entry_day": 10,
                        "exit_day": 30,
                        "entry_price": 450.0,
                        "exit_price": 470.0,
                        "drawdown_at_entry": 0.06,
                        "leveraged_return": 0.12,
                        "exit_reason": "target",
                    },
                    {
                        "entry_day": 50,
                        "exit_day": 80,
                        "entry_price": 440.0,
                        "exit_price": 420.0,
                        "drawdown_at_entry": 0.08,
                        "leveraged_return": -0.05,
                        "exit_reason": "stop",
                    },
                ],
                "equity_curve": [10000.0, 11200.0, 10640.0],
            },
        ]
    )
    outputs = {"strategy.backtest-all": backtest_data}
    result = build_trade_logs_html(outputs, date="2026-01-15")
    assert "<!DOCTYPE html>" in result
    assert "equityChart" in result
    assert "chart.js" in result.lower() or "Chart" in result
    assert "TQQQ" in result
    assert "QQQ" in result
    assert "$450.00" in result
    assert "$470.00" in result
    assert "TARGET" in result
    assert "Trade Logs" in result
    assert "Equity Curve" in result
    assert "10000" in result
    assert "11200" in result


def test_build_trade_logs_html_empty():
    """Trade logs returns empty string when no backtest data."""
    result = build_trade_logs_html({}, date="2026-01-15")
    assert result == ""


def test_build_trade_logs_html_summary_table():
    """Trade logs page has a summary table with key metrics."""
    backtest_data = json.dumps(
        [
            {
                "leveraged_ticker": "UPRO",
                "underlying_ticker": "SPY",
                "leverage": 3.0,
                "entry_threshold": 0.05,
                "profit_target": 0.10,
                "period": "2y",
                "total_days": 500,
                "total_return": 0.25,
                "sharpe_ratio": 1.2,
                "win_rate": 0.65,
                "max_drawdown": 0.10,
                "trade_count": 8,
                "trades": [],
                "equity_curve": [10000.0],
            },
        ]
    )
    outputs = {"strategy.backtest-all": backtest_data}
    result = build_trade_logs_html(outputs, date="2026-01-15")
    assert "Strategy Performance Summary" in result
    assert "UPRO" in result
    assert "SPY" in result
    assert "1.200" in result  # sharpe
    assert "65.0%" in result  # win rate
    assert "+25.0%" in result  # total return


def test_build_trade_logs_html_multiple_etfs():
    """Trade logs page shows multiple ETF equity curves."""
    backtest_data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "leverage": 3.0,
                "entry_threshold": 0.05,
                "profit_target": 0.10,
                "period": "2y",
                "total_days": 500,
                "total_return": 0.35,
                "sharpe_ratio": 1.5,
                "win_rate": 0.7,
                "max_drawdown": 0.12,
                "trade_count": 3,
                "trades": [],
                "equity_curve": [10000.0, 11000.0, 12000.0],
            },
            {
                "leveraged_ticker": "SOXL",
                "underlying_ticker": "SOXX",
                "leverage": 3.0,
                "entry_threshold": 0.08,
                "profit_target": 0.10,
                "period": "2y",
                "total_days": 500,
                "total_return": 0.50,
                "sharpe_ratio": 1.8,
                "win_rate": 0.75,
                "max_drawdown": 0.15,
                "trade_count": 4,
                "trades": [],
                "equity_curve": [10000.0, 11500.0, 13000.0, 15000.0],
            },
        ]
    )
    outputs = {"strategy.backtest-all": backtest_data}
    result = build_trade_logs_html(outputs, date="2026-01-15")
    assert "TQQQ" in result
    assert "SOXL" in result
    # Both should be in chart datasets
    assert "12000" in result
    assert "15000" in result


# --- Market-Moving Events tests ---


def test_build_html_report_market_risks_section():
    """Market risks section shows when geopolitical events exist."""
    data = json.dumps(
        {
            "risk_level": "MEDIUM",
            "total_events": 30,
            "high_impact_count": 2,
            "events_by_category": {
                "TRADE_WAR": 15,
                "MILITARY": 10,
                "SANCTIONS": 5,
            },
            "affected_sectors": {"tech": 20, "energy": 10},
        }
    )
    run = _make_run([_ok("geopolitical.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "Market-Moving Events" in html
    assert 'id="risks"' in html
    assert "Trade Wars" in html
    assert "Military Conflicts" in html
    assert "Economic Sanctions" in html
    assert "TQQQ" in html  # affected ETF badge
    assert "supply chain" in html.lower() or "tariff" in html.lower()


def test_build_html_report_market_risks_empty():
    """Market risks section hidden when no geopolitical data."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "Market-Moving Events" not in html


def test_build_html_report_nav_has_risks_link():
    """Nav menu includes risks link."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert 'href="#risks"' in html


def test_build_html_report_trade_logs_link():
    """Nav includes link to trade logs page."""
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "trade-logs-2026-01-15.html" in html
    assert "Trade Logs" in html


# --- Publisher trade logs test ---


def test_write_report_generates_trade_logs(tmp_path, monkeypatch):
    """Publisher generates trade-logs HTML alongside the report."""
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR",
        tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    backtest_data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "leverage": 3.0,
                "entry_threshold": 0.05,
                "profit_target": 0.10,
                "period": "2y",
                "total_days": 500,
                "total_return": 0.35,
                "sharpe_ratio": 1.5,
                "win_rate": 0.7,
                "max_drawdown": 0.12,
                "trade_count": 3,
                "trades": [],
                "equity_curve": [10000.0, 11000.0, 12000.0],
            },
        ]
    )
    run = _make_run([_ok("strategy.backtest-all", backtest_data)])
    write_report(run, date="2026-01-15")

    trade_logs_path = tmp_path / "docs" / "reports" / "trade-logs-2026-01-15.html"
    assert trade_logs_path.exists()
    content = trade_logs_path.read_text()
    assert "TQQQ" in content
    assert "equityChart" in content


# --- Git publish tests ---


def test_git_publish_success(monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._PROJECT_ROOT",
        Path("/fake"),
    )
    with patch("app.scheduler.publisher.subprocess.run") as mock:
        result = git_publish()
    assert result is True
    assert mock.call_count == 3


def test_git_publish_failure(monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._PROJECT_ROOT",
        Path("/fake"),
    )
    with patch(
        "app.scheduler.publisher.subprocess.run",
        side_effect=sp.CalledProcessError(1, "git"),
    ):
        result = git_publish()
    assert result is False


# --- Trade logs nav bar test ---


def test_build_trade_logs_html_has_nav():
    """Trade logs page should include unified nav bar."""
    data = json.dumps(
        [
            {
                "leveraged_ticker": "TQQQ",
                "underlying_ticker": "QQQ",
                "strategy_type": "ath_mean_reversion",
                "leverage": 3.0,
                "entry_threshold": 0.05,
                "profit_target": 0.10,
                "period": "2y",
                "total_days": 500,
                "total_return": 0.25,
                "sharpe_ratio": 1.2,
                "win_rate": 0.65,
                "max_drawdown": 0.10,
                "trade_count": 2,
                "trades": [
                    {
                        "entry_day": 10,
                        "exit_day": 20,
                        "entry_date": "2024-06-15",
                        "exit_date": "2024-06-28",
                        "entry_price": 100.0,
                        "exit_price": 110.0,
                        "drawdown_at_entry": 0.06,
                        "leveraged_return": 0.30,
                        "exit_reason": "target",
                    },
                ],
                "equity_curve": [10000.0, 13000.0],
            },
        ]
    )
    outputs = {"strategy.backtest-all": data}
    html = build_trade_logs_html(outputs, date="2026-02-12")
    assert html
    assert "nav-menu" in html
    assert "2026-02-12.html" in html  # Dashboard link
    assert "forecasts-2026-02-12.html" in html  # Forecasts link
    # Date columns should show actual dates
    assert "2024-06-15" in html
    assert "2024-06-28" in html
    assert "Entry Date" in html


# --- Forecasts page tests ---


def test_build_forecasts_html_basic():
    """Forecasts page should render forecast table."""
    forecast_data = json.dumps(
        {
            "date": "2026-02-12",
            "forecasts": [
                {
                    "leveraged_ticker": "TQQQ",
                    "underlying_ticker": "QQQ",
                    "signal_state": "SIGNAL",
                    "current_drawdown_pct": -0.06,
                    "confidence_level": "MEDIUM",
                    "entry_probability": 0.72,
                    "expected_return_pct": 0.025,
                    "expected_hold_days": 12,
                    "best_strategy": "ath_mean_reversion",
                    "factor_scores": {},
                },
                {
                    "leveraged_ticker": "UPRO",
                    "underlying_ticker": "SPY",
                    "signal_state": "WATCH",
                    "current_drawdown_pct": -0.02,
                    "confidence_level": "LOW",
                    "entry_probability": 0.18,
                    "expected_return_pct": -0.08,
                    "expected_hold_days": 20,
                    "best_strategy": "rsi_oversold",
                    "factor_scores": {},
                },
            ],
            "actionable_count": 1,
        }
    )
    outputs = {"strategy.forecast": forecast_data}
    html = build_forecasts_html(outputs, date="2026-02-12")
    assert html
    assert "TQQQ" in html
    assert "UPRO" in html
    assert "nav-menu" in html
    assert "Forecasts" in html
    assert "Entry Prob" in html
    assert "actionable" in html


def test_build_forecasts_html_with_accuracy():
    """Forecasts page should show accuracy KPIs when data available."""
    forecast_data = json.dumps(
        {
            "date": "2026-02-12",
            "forecasts": [
                {
                    "leveraged_ticker": "TQQQ",
                    "underlying_ticker": "QQQ",
                    "signal_state": "SIGNAL",
                    "current_drawdown_pct": -0.06,
                    "confidence_level": "MEDIUM",
                    "entry_probability": 0.72,
                    "expected_return_pct": 0.025,
                    "expected_hold_days": 12,
                    "best_strategy": "ath_mean_reversion",
                    "factor_scores": {},
                },
            ],
            "actionable_count": 1,
        }
    )
    accuracy_data = json.dumps(
        {
            "total_verifications": 20,
            "correct_count": 14,
            "hit_rate": 0.70,
            "recent_hit_rate": 0.80,
            "trend": "IMPROVING",
        }
    )
    outputs = {
        "strategy.forecast": forecast_data,
        "strategy.verify": accuracy_data,
    }
    html = build_forecasts_html(outputs, date="2026-02-12")
    assert html
    assert "Forecast Accuracy" in html
    assert "Hit Rate" in html
    assert "Trend" in html
    # IMPROVING maps to TARGET badge (green)
    assert "badge-green" in html


def test_build_forecasts_html_empty():
    """Empty forecast data should return empty string."""
    html = build_forecasts_html({}, date="2026-02-12")
    assert html == ""


def test_write_report_generates_forecasts(tmp_path, monkeypatch):
    """Publisher generates forecasts HTML alongside the report."""
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR",
        tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    forecast_data = json.dumps(
        {
            "date": "2026-01-15",
            "forecasts": [
                {
                    "leveraged_ticker": "TQQQ",
                    "underlying_ticker": "QQQ",
                    "signal_state": "SIGNAL",
                    "current_drawdown_pct": -0.06,
                    "confidence_level": "MEDIUM",
                    "entry_probability": 0.72,
                    "expected_return_pct": 0.025,
                    "expected_hold_days": 12,
                    "best_strategy": "ath_mean_reversion",
                    "factor_scores": {},
                },
            ],
            "actionable_count": 1,
        }
    )
    run = _make_run([_ok("strategy.forecast", forecast_data)])
    write_report(run, date="2026-01-15")

    forecasts_path = tmp_path / "docs" / "reports" / "forecasts-2026-01-15.html"
    assert forecasts_path.exists()
    content = forecasts_path.read_text()
    assert "TQQQ" in content

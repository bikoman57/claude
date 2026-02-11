from __future__ import annotations

import json
import subprocess as sp
from pathlib import Path
from unittest.mock import patch

from app.scheduler.html_report import build_html_report, build_index_html
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
    run = _make_run([_ok("etf.scan", "[]"), _fail("macro.dashboard")])
    html = build_html_report(run, date="2026-01-15")
    assert "Dashboard" in html
    assert ">1</span>/2 OK" in html
    assert ">1</span> failed" in html


def test_build_html_report_kpi_vix():
    data = json.dumps({
        "vix": 22.5,
        "vix_regime": "ELEVATED",
        "fed_trajectory": "CUTTING",
    })
    run = _make_run([_ok("macro.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "22.5" in html
    assert "ELEVATED" in html
    assert "CUTTING" in html
    assert "kpi-card" in html
    assert "kpi-bar-red" in html  # ELEVATED → red


def test_build_html_report_kpi_fed_rate():
    data = json.dumps({
        "vix": 15.0,
        "vix_regime": "NORMAL",
        "fed_trajectory": "HIKING",
        "fed_funds_rate": 5.25,
    })
    run = _make_run([_ok("macro.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "5.25%" in html
    assert "HIKING" in html


def test_build_html_report_kpi_yields():
    data = json.dumps({
        "curve_status": "INVERTED",
        "spread_3m_10y": -0.42,
    })
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
    data = json.dumps({
        "overall_sentiment": "BEARISH",
        "total_articles": 42,
    })
    run = _make_run([_ok("news.summary", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "BEARISH" in html
    assert "42 articles" in html


def test_build_html_report_kpi_strip_all_sources():
    run = _make_run([
        _ok("macro.dashboard", json.dumps({
            "vix": 18.5, "vix_regime": "NORMAL",
            "fed_trajectory": "CUTTING",
        })),
        _ok("macro.yields", json.dumps({
            "curve_status": "NORMAL", "spread_3m_10y": 0.35,
        })),
        _ok("geopolitical.summary", json.dumps({
            "risk_level": "LOW", "total_events": 1,
        })),
        _ok("news.summary", json.dumps({
            "overall_sentiment": "BULLISH", "total_articles": 99,
        })),
    ])
    html = build_html_report(run, date="2026-01-15")
    # 5 KPI cards: VIX, Fed, Yield, Geo, News
    assert html.count("kpi-card") >= 5
    assert "kpi-strip" in html


def test_build_html_report_etf_signals():
    data = json.dumps([{
        "leveraged_ticker": "TQQQ",
        "underlying_ticker": "QQQ",
        "state": "SIGNAL",
        "underlying_drawdown_pct": 0.072,
        "underlying_ath": 520.0,
        "underlying_current": 482.56,
    }])
    run = _make_run([_ok("etf.scan", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "TQQQ" in html
    assert "QQQ" in html
    assert "SIGNAL" in html
    assert "$520.00" in html
    assert "$482.56" in html


def test_build_html_report_etf_signals_with_pl():
    data = json.dumps([{
        "leveraged_ticker": "TQQQ",
        "underlying_ticker": "QQQ",
        "state": "ACTIVE",
        "underlying_drawdown_pct": 0.05,
        "current_pl_pct": 0.08,
    }])
    run = _make_run([_ok("etf.scan", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "pct-up" in html
    assert "+8.0%" in html


def test_build_html_report_strategy():
    data = json.dumps([{
        "leveraged_ticker": "SOXL",
        "improvement_reason": "Better Sharpe at 10%",
        "backtest_sharpe": 2.15,
        "backtest_win_rate": 0.75,
        "backtest_total_return": 0.42,
    }])
    run = _make_run([_ok("strategy.proposals", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "SOXL" in html
    assert "Better Sharpe" in html
    assert "2.15" in html
    assert "75.0%" in html
    assert "+42.0%" in html


def test_build_html_report_market_indicators():
    data = json.dumps({
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
    })
    run = _make_run([_ok("statistics.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "RISK_OFF" in html
    assert "Gold" in html
    assert "$2,050.50" in html
    assert "Oil" in html
    assert "DXY" in html
    assert "DECOUPLING" in html
    assert "SPY-IWM" in html


def test_build_html_report_market_indicators_officials():
    run = _make_run([
        _ok("social.summary", json.dumps({
            "officials": {
                "overall_tone": "HAWKISH",
                "policy_direction": "CONTRACTIONARY",
            },
        })),
    ])
    html = build_html_report(run, date="2026-01-15")
    assert "HAWKISH" in html
    assert "CONTRACTIONARY" in html


def test_build_html_report_module_status_pills():
    run = _make_run([_ok("etf.scan", "[]"), _fail("macro.dashboard")])
    html = build_html_report(run, date="2026-01-15")
    assert "module-grid" in html
    assert "module-pill-ok" in html
    assert "module-pill-fail" in html
    assert "etf.scan" in html
    assert "macro.dashboard" in html


def test_build_html_report_xss_safety():
    data = json.dumps({
        "vix": 20.0,
        "vix_regime": "<script>alert('xss')</script>",
        "fed_trajectory": "CUTTING",
    })
    run = _make_run([_ok("macro.dashboard", data)])
    html = build_html_report(run, date="2026-01-15")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_build_html_report_two_col_grid():
    run = _make_run([
        _ok("strategy.proposals", json.dumps([{
            "leveraged_ticker": "TQQQ",
            "improvement_reason": "test",
        }])),
        _ok("statistics.dashboard", json.dumps({
            "risk_indicators": {"risk_assessment": "NEUTRAL"},
        })),
    ])
    html = build_html_report(run, date="2026-01-15")
    assert "grid-2col" in html


def test_build_html_report_responsive():
    run = _make_run()
    html = build_html_report(run, date="2026-01-15")
    assert "@media" in html
    assert "768px" in html


def test_build_html_report_all_sections():
    run = _make_run([
        _ok("macro.dashboard", json.dumps({
            "vix": 12.0, "vix_regime": "CALM",
            "fed_trajectory": "HOLDING",
        })),
        _ok("macro.yields", json.dumps({
            "curve_status": "NORMAL", "spread_3m_10y": 0.5,
        })),
        _ok("geopolitical.summary", json.dumps({
            "risk_level": "LOW", "total_events": 2,
        })),
        _ok("social.summary", json.dumps({
            "officials": {"overall_tone": "NEUTRAL"},
        })),
        _ok("news.summary", json.dumps({
            "overall_sentiment": "BULLISH", "total_articles": 30,
        })),
        _ok("statistics.dashboard", json.dumps({
            "risk_indicators": {"risk_assessment": "LOW"},
        })),
        _ok("etf.scan", json.dumps([{
            "leveraged_ticker": "TQQQ",
            "underlying_ticker": "QQQ",
            "state": "WATCH",
            "underlying_drawdown_pct": 0.03,
        }])),
        _ok("strategy.proposals", json.dumps([{
            "leveraged_ticker": "SOXL",
            "improvement_reason": "Good entry",
        }])),
    ])
    html = build_html_report(run, date="2026-02-01")
    assert "CALM" in html
    assert "TQQQ" in html
    assert "SOXL" in html
    assert "All Reports" in html
    assert "kpi-strip" in html
    assert "grid-2col" in html
    assert "module-grid" in html


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
        "app.scheduler.publisher._DOCS_DIR", tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    run = _make_run([_ok("etf.scan", "[]")])
    path = write_report(run, date="2026-01-15")

    assert path.exists()
    assert path.name == "2026-01-15.html"
    assert (tmp_path / "docs" / "index.html").exists()


def test_write_report_index_includes_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR", tmp_path / "docs",
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
        "app.scheduler.publisher._DOCS_DIR", tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    run1 = _make_run([_ok("etf.scan", "[]")])
    run2 = _make_run([_ok("macro.dashboard", json.dumps({
        "vix": 30.0, "vix_regime": "HIGH",
        "fed_trajectory": "HIKING",
    }))])
    write_report(run1, date="2026-01-15")
    write_report(run2, date="2026-01-15")

    content = (
        tmp_path / "docs" / "reports" / "2026-01-15.html"
    ).read_text()
    assert "HIGH" in content


def test_discover_report_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR", tmp_path,
    )
    (tmp_path / "2026-01-13.html").write_text("<html></html>")
    (tmp_path / "2026-01-15.html").write_text("<html></html>")
    (tmp_path / "2026-01-14.html").write_text("<html></html>")
    (tmp_path / "not-a-date.html").write_text("<html></html>")

    dates = _discover_report_dates()
    assert dates == ["2026-01-15", "2026-01-14", "2026-01-13"]


def test_nojekyll_created(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._DOCS_DIR", tmp_path / "docs",
    )
    monkeypatch.setattr(
        "app.scheduler.publisher._REPORTS_DIR",
        tmp_path / "docs" / "reports",
    )
    write_report(_make_run(), date="2026-01-15")
    assert (tmp_path / "docs" / ".nojekyll").exists()


# --- Git publish tests ---


def test_git_publish_success(monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._PROJECT_ROOT", Path("/fake"),
    )
    with patch("app.scheduler.publisher.subprocess.run") as mock:
        result = git_publish()
    assert result is True
    assert mock.call_count == 3


def test_git_publish_failure(monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.publisher._PROJECT_ROOT", Path("/fake"),
    )
    with patch(
        "app.scheduler.publisher.subprocess.run",
        side_effect=sp.CalledProcessError(1, "git"),
    ):
        result = git_publish()
    assert result is False

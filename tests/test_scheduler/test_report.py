from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.scheduler.report import build_report_text, send_daily_report
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


def test_build_report_empty_run():
    run = _make_run()
    text = build_report_text(run)
    assert "DAILY SWING TRADING REPORT" in text
    assert "not financial advice" in text


def test_build_report_with_modules():
    macro_data = json.dumps({
        "vix_regime": "ELEVATED",
    })
    rates_data = json.dumps({
        "trajectory": "CUTTING",
    })
    run = _make_run([
        _ok("macro.dashboard", macro_data),
        _ok("macro.rates", rates_data),
        _ok("etf.signals", "[]"),
    ])
    text = build_report_text(run)
    assert "MARKET OVERVIEW" in text
    assert "ELEVATED" in text


def test_build_report_with_failures():
    run = _make_run([_fail("macro.dashboard")])
    text = build_report_text(run)
    assert "WARNINGS" in text
    assert "macro" in text


def test_build_report_geopolitical():
    geo_data = json.dumps({
        "risk_level": "HIGH",
        "total_events": 5,
    })
    run = _make_run([_ok("geopolitical.summary", geo_data)])
    text = build_report_text(run)
    assert "GEOPOLITICAL" in text
    assert "HIGH" in text


def test_build_report_news():
    news_data = json.dumps({
        "sentiment": "BEARISH",
        "total_articles": 42,
    })
    run = _make_run([_ok("news.summary", news_data)])
    text = build_report_text(run)
    assert "NEWS" in text
    assert "BEARISH" in text


def test_build_report_etf_signals():
    signals = json.dumps([
        {
            "leveraged_ticker": "TQQQ",
            "state": "SIGNAL",
            "underlying_drawdown_pct": 0.072,
        },
    ])
    run = _make_run([_ok("etf.signals", signals)])
    text = build_report_text(run)
    assert "ENTRY SIGNALS" in text
    assert "TQQQ" in text


def test_build_report_strategy():
    proposals = json.dumps([
        {
            "leveraged_ticker": "SOXL",
            "improvement_reason": "Better Sharpe at 10%",
        },
    ])
    run = _make_run([_ok("strategy.proposals", proposals)])
    text = build_report_text(run)
    assert "STRATEGY INSIGHTS" in text
    assert "SOXL" in text


@pytest.mark.asyncio
async def test_send_daily_report_no_config():
    """Missing Telegram config returns False."""
    run = _make_run()
    with patch(
        "app.scheduler.report.TelegramConfig.from_env",
        side_effect=ValueError("missing"),
    ):
        result = await send_daily_report(run)
    assert result is False


@pytest.mark.asyncio
async def test_send_daily_report_success():
    run = _make_run([_ok("etf.signals", "[]")])
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "app.scheduler.report.TelegramConfig.from_env",
        ),
        patch(
            "app.scheduler.report.TelegramClient",
            return_value=mock_client,
        ),
    ):
        result = await send_daily_report(run)
    assert result is True
    mock_client.send_message.assert_called_once()

"""Tests for cross-run continuity context in scheduled runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agile.models import (
    Sprint,
    SprintStatus,
    SprintTask,
    StandupEntry,
    StandupRecord,
    TaskPriority,
    TaskStatus,
)
from app.scheduler.config import SchedulerConfig
from app.scheduler.scheduled_run import (
    RunSession,
    _build_continuity_context,
    _claude_log_sort_key,
    _find_previous_claude_log,
)

_ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")


def _make_config(tmp_path: Path) -> SchedulerConfig:
    """Build a minimal SchedulerConfig for testing."""
    return SchedulerConfig(
        project_dir=tmp_path,
        uv_executable=Path("uv"),
        claude_executable=Path("claude"),
        claude_timeout=60,
        logs_dir=tmp_path / "logs",
    )


# ── _claude_log_sort_key ─────────────────────────────────


def test_sort_key_pre_market() -> None:
    p = Path("2026-02-13_pre-market_claude.log")
    assert _claude_log_sort_key(p) == "2026-02-13_0"


def test_sort_key_post_market() -> None:
    p = Path("2026-02-13_post-market_claude.log")
    assert _claude_log_sort_key(p) == "2026-02-13_1"


def test_sort_key_chronological_order() -> None:
    pre = Path("2026-02-13_pre-market_claude.log")
    post = Path("2026-02-13_post-market_claude.log")
    assert _claude_log_sort_key(pre) < _claude_log_sort_key(post)


def test_sort_key_cross_day() -> None:
    yesterday_post = Path("2026-02-12_post-market_claude.log")
    today_pre = Path("2026-02-13_pre-market_claude.log")
    assert _claude_log_sort_key(yesterday_post) < _claude_log_sort_key(today_pre)


# ── _find_previous_claude_log ─────────────────────────────


def test_find_previous_log_no_dir(tmp_path: Path) -> None:
    result = _find_previous_claude_log(
        RunSession.PRE_MARKET,
        tmp_path / "nonexistent",
        datetime(2026, 2, 13, tzinfo=UTC),
    )
    assert result is None


def test_find_previous_log_no_files(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    result = _find_previous_claude_log(
        RunSession.PRE_MARKET,
        logs,
        datetime(2026, 2, 13, tzinfo=UTC),
    )
    assert result is None


def test_find_previous_log_pre_finds_yesterday_post(
    tmp_path: Path,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    log = logs / "2026-02-12_post-market_claude.log"
    log.write_text("analysis output")
    result = _find_previous_claude_log(
        RunSession.PRE_MARKET,
        logs,
        datetime(2026, 2, 13, 7, 0, tzinfo=_ISRAEL_TZ),
    )
    assert result == log


def test_find_previous_log_post_finds_today_pre(
    tmp_path: Path,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    log = logs / "2026-02-13_pre-market_claude.log"
    log.write_text("morning analysis")
    result = _find_previous_claude_log(
        RunSession.POST_MARKET,
        logs,
        datetime(2026, 2, 13, 17, 0, tzinfo=_ISRAEL_TZ),
    )
    assert result == log


def test_find_previous_log_skips_empty(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    log = logs / "2026-02-12_post-market_claude.log"
    log.write_text("")
    result = _find_previous_claude_log(
        RunSession.PRE_MARKET,
        logs,
        datetime(2026, 2, 13, 7, 0, tzinfo=_ISRAEL_TZ),
    )
    assert result is None


def test_find_previous_log_picks_most_recent(
    tmp_path: Path,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "2026-02-11_post-market_claude.log").write_text("old")
    newer = logs / "2026-02-12_post-market_claude.log"
    newer.write_text("newer")
    result = _find_previous_claude_log(
        RunSession.PRE_MARKET,
        logs,
        datetime(2026, 2, 13, 7, 0, tzinfo=_ISRAEL_TZ),
    )
    assert result == newer


# ── _build_continuity_context ─────────────────────────────


def test_continuity_empty_no_data(
    tmp_path: Path, monkeypatch: object,
) -> None:
    import app.agile.store as store

    monkeypatch.setattr(store, "get_current_sprint", lambda **kw: None)  # type: ignore[attr-defined]
    monkeypatch.setattr(store, "load_standup", lambda *a, **kw: None)  # type: ignore[attr-defined]
    config = _make_config(tmp_path)
    result = _build_continuity_context(RunSession.PRE_MARKET, config)
    assert result == ""


def test_continuity_includes_signals(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "signals.json").write_text(
        json.dumps([
            {
                "leveraged_ticker": "TQQQ",
                "state": "ALERT",
                "underlying_drawdown_pct": -0.05,
                "current_pl_pct": None,
            },
        ]),
    )
    config = _make_config(tmp_path)
    result = _build_continuity_context(RunSession.PRE_MARKET, config)
    assert "TQQQ" in result
    assert "ALERT" in result
    assert "5.0%" in result


def test_continuity_includes_forecast_accuracy(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "forecast_accuracy.json").write_text(
        json.dumps({
            "hit_rate": 0.625,
            "recent_hit_rate": 0.7,
            "trend": "STABLE",
            "total_verifications": 16,
        }),
    )
    config = _make_config(tmp_path)
    result = _build_continuity_context(RunSession.PRE_MARKET, config)
    assert "62%" in result
    assert "STABLE" in result


def test_continuity_graceful_on_corrupt_json(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "signals.json").write_text("{not valid json")
    config = _make_config(tmp_path)
    result = _build_continuity_context(RunSession.PRE_MARKET, config)
    assert isinstance(result, str)  # no crash


def test_continuity_includes_previous_analysis(
    tmp_path: Path,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    content = "MARKET OVERVIEW\n" + "x" * 5000
    (logs / "2026-02-12_post-market_claude.log").write_text(content)
    config = _make_config(tmp_path)
    result = _build_continuity_context(RunSession.PRE_MARKET, config)
    assert "Previous Analysis" in result
    assert "MARKET OVERVIEW" in result
    assert "5,0" in result or "chars total" in result


def test_continuity_includes_sprint(monkeypatch: object) -> None:
    import app.agile.store as store

    mock = Sprint(
        number=3,
        start_date="2026-02-10",
        end_date="2026-02-14",
        goals=["Improve accuracy"],
        tasks=[
            SprintTask(
                id="S3-T1",
                title="task1",
                description="",
                assignee_department="trading",
                priority=TaskPriority.HIGH,
                status=TaskStatus.DONE,
            ),
            SprintTask(
                id="S3-T2",
                title="task2",
                description="",
                assignee_department="research",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.BLOCKED,
            ),
        ],
        status=SprintStatus.ACTIVE,
    )
    monkeypatch.setattr(store, "get_current_sprint", lambda **kw: mock)  # type: ignore[attr-defined]
    config = _make_config(Path("c:/tmp/fake"))
    result = _build_continuity_context(RunSession.PRE_MARKET, config)
    assert "Sprint 3" in result
    assert "1/2 done" in result
    assert "1 blocked" in result
    assert "Improve accuracy" in result


def test_continuity_includes_standup(monkeypatch: object) -> None:
    import app.agile.store as store

    record = StandupRecord(
        date="2026-02-13",
        sprint_number=1,
        session="pre-market",
        entries=[
            StandupEntry(
                department="trading",
                agent="swing-screener",
                yesterday="scanned signals",
                today="scan for entries",
                blockers="",
            ),
            StandupEntry(
                department="risk",
                agent="risk-manager",
                yesterday="checked limits",
                today="monitor exposure",
                blockers="portfolio API down",
            ),
        ],
        summary="Sprint 1: 0/0 tasks done",
    )
    monkeypatch.setattr(store, "load_standup", lambda *a, **kw: record)  # type: ignore[attr-defined]
    config = _make_config(Path("c:/tmp/fake"))
    result = _build_continuity_context(RunSession.PRE_MARKET, config)
    assert "Standup" in result
    assert "trading" in result
    assert "BLOCKED: portfolio API down" in result

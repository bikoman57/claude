"""Tests for DevOps health monitoring."""

from __future__ import annotations

from pathlib import Path

from app.devops.health import (
    get_all_module_health,
    get_module_health,
    get_system_health,
    load_pipeline_history,
    record_pipeline_run,
)
from app.scheduler.runner import ModuleResult, SchedulerRun


def _make_run(
    ok_modules: list[str],
    failed_modules: list[str] | None = None,
) -> SchedulerRun:
    failed_modules = failed_modules or []
    results = [ModuleResult(n, True, "ok", "", 5.0) for n in ok_modules]
    results.extend(ModuleResult(n, False, "", "err", 5.0) for n in failed_modules)
    return SchedulerRun(
        started_at="2026-02-12T07:00:00",
        finished_at="2026-02-12T07:05:00",
        results=results,
        total_modules=len(ok_modules) + len(failed_modules),
        succeeded=len(ok_modules),
        failed=len(failed_modules),
    )


class TestRecordPipelineRun:
    def test_record_and_load(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        run = _make_run(["mod.a", "mod.b"], ["mod.c"])

        record_pipeline_run(run, "pre-market", path=history_path)
        history = load_pipeline_history(days=7, path=history_path)
        assert len(history) == 1
        assert history[0].modules_ok == 2
        assert history[0].modules_total == 3

    def test_multiple_records(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        run1 = _make_run(["mod.a", "mod.b"])
        run2 = _make_run(["mod.a"], ["mod.b"])

        record_pipeline_run(run1, "pre-market", path=history_path)
        record_pipeline_run(run2, "post-market", path=history_path)

        history = load_pipeline_history(days=7, path=history_path)
        assert len(history) == 2


class TestModuleHealth:
    def test_no_history(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        health = get_module_health("mod.a", path=history_path)
        assert health.success_rate_7d == 0.0
        assert health.trend == "unknown"

    def test_all_success(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        for _ in range(5):
            run = _make_run(["mod.a", "mod.b"])
            record_pipeline_run(run, "pre-market", path=history_path)

        health = get_module_health("mod.a", path=history_path)
        assert health.success_rate_7d == 100.0
        assert health.last_failure is None

    def test_with_failures(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        # 3 successes, 2 failures
        for i in range(5):
            run = _make_run(["mod.a"]) if i < 3 else _make_run([], ["mod.a"])
            record_pipeline_run(run, "pre-market", path=history_path)

        health = get_module_health("mod.a", path=history_path)
        assert health.success_rate_7d == 60.0
        assert health.last_failure is not None


class TestSystemHealth:
    def test_no_history(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        health = get_system_health(path=history_path)
        assert health.grade == "F"
        assert health.score == 0.0

    def test_healthy_system(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        run = _make_run(["a", "b", "c", "d", "e"])
        record_pipeline_run(run, "pre-market", path=history_path)

        health = get_system_health(path=history_path)
        assert health.score > 0.8
        assert health.grade in ("A", "B")

    def test_degraded_system(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        run = _make_run(["a", "b"], ["c", "d", "e"])
        record_pipeline_run(run, "pre-market", path=history_path)

        health = get_system_health(path=history_path)
        assert health.score < 0.8


class TestGetAllModuleHealth:
    def test_returns_all_modules(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        run = _make_run(["mod.a", "mod.b", "mod.c"])
        record_pipeline_run(run, "pre-market", path=history_path)

        modules = get_all_module_health(path=history_path)
        names = [m.name for m in modules]
        assert "mod.a" in names
        assert "mod.b" in names
        assert "mod.c" in names

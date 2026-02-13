"""Tests for postmortem system."""

from __future__ import annotations

from pathlib import Path

from app.agile.postmortem import (
    PostmortemItem,
    detect_failures,
    load_postmortems,
    save_postmortem,
    weekly_postmortem_summary,
)
from app.scheduler.runner import ModuleResult, SchedulerRun


def _make_run(
    succeeded: int = 20,
    failed: int = 0,
) -> SchedulerRun:
    results = [
        ModuleResult(f"module.{i}", True, "ok", "", 5.0) for i in range(succeeded)
    ]
    results.extend(
        ModuleResult(f"failed.{i}", False, "", f"Error in module {i}", 5.0)
        for i in range(failed)
    )
    return SchedulerRun(
        started_at="2026-02-12T07:00:00",
        finished_at="2026-02-12T07:05:00",
        results=results,
        total_modules=succeeded + failed,
        succeeded=succeeded,
        failed=failed,
    )


class TestDetectFailures:
    def test_no_failures(self) -> None:
        run = _make_run(succeeded=21, failed=0)
        items = detect_failures(pipeline_run=run, trade_outcomes=[])
        assert items == []

    def test_pipeline_failure(self) -> None:
        run = _make_run(succeeded=18, failed=3)
        items = detect_failures(pipeline_run=run, trade_outcomes=[])
        assert len(items) == 1
        assert items[0].category == "pipeline_failure"
        assert items[0].severity == "major"

    def test_system_outage(self) -> None:
        run = _make_run(succeeded=5, failed=16)
        items = detect_failures(pipeline_run=run, trade_outcomes=[])
        assert len(items) == 1
        assert items[0].category == "system_outage"
        assert items[0].severity == "critical"


class TestPostmortemPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        item = PostmortemItem(
            id="PM-2026-02-12-001",
            date="2026-02-12",
            category="pipeline_failure",
            severity="major",
            title="Test failure",
            sprint_number=1,
        )
        save_postmortem(item, tmp_path)
        loaded = load_postmortems(path=tmp_path)
        assert len(loaded) == 1
        assert loaded[0].title == "Test failure"

    def test_filter_by_sprint(self, tmp_path: Path) -> None:
        for i, sn in enumerate([1, 1, 2], 1):
            save_postmortem(
                PostmortemItem(
                    id=f"PM-2026-02-12-{i:03d}",
                    date="2026-02-12",
                    category="test",
                    severity="minor",
                    title=f"PM {i}",
                    sprint_number=sn,
                ),
                tmp_path,
            )
        sprint_1 = load_postmortems(sprint_number=1, path=tmp_path)
        assert len(sprint_1) == 2


class TestWeeklyPostmortemSummary:
    def test_no_postmortems(self, tmp_path: Path) -> None:
        summary = weekly_postmortem_summary(1, path=tmp_path)
        assert "No postmortems" in summary

    def test_with_postmortems(self, tmp_path: Path) -> None:
        save_postmortem(
            PostmortemItem(
                id="PM-2026-02-12-001",
                date="2026-02-12",
                category="test",
                severity="major",
                title="Big failure",
                sprint_number=1,
            ),
            tmp_path,
        )
        summary = weekly_postmortem_summary(1, path=tmp_path)
        assert "1 total" in summary
        assert "Big failure" in summary

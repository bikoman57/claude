"""Tests for Agile ceremony generation."""

from __future__ import annotations

from app.agile.ceremonies import generate_retro, generate_standup
from app.agile.models import Sprint, SprintStatus, SprintTask, TaskPriority, TaskStatus
from app.scheduler.runner import ModuleResult, SchedulerRun


def _make_pipeline_run(
    succeeded: int = 20,
    failed: int = 1,
) -> SchedulerRun:
    """Create a test SchedulerRun."""
    results = [
        ModuleResult(f"module.{i}", True, "ok", "", 5.0) for i in range(succeeded)
    ]
    results.extend(
        ModuleResult(f"failed.{i}", False, "", "error", 5.0) for i in range(failed)
    )
    return SchedulerRun(
        started_at="2026-02-12T07:00:00",
        finished_at="2026-02-12T07:05:00",
        results=results,
        total_modules=succeeded + failed,
        succeeded=succeeded,
        failed=failed,
    )


class TestGenerateStandup:
    def test_basic_standup(self) -> None:
        sprint = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            status=SprintStatus.ACTIVE,
        )
        run = _make_pipeline_run()

        standup = generate_standup(sprint, "pre-market", pipeline_run=run)
        assert standup.sprint_number == 1
        assert standup.session == "pre-market"
        assert len(standup.entries) == 5  # 5 departments
        assert standup.summary != ""

    def test_standup_with_failures(self) -> None:
        sprint = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            status=SprintStatus.ACTIVE,
        )
        run = _make_pipeline_run(succeeded=15, failed=6)

        standup = generate_standup(sprint, "post-market", pipeline_run=run)
        ops_entry = next(e for e in standup.entries if e.department == "operations")
        assert "failed" in ops_entry.blockers.lower() or "Failed" in ops_entry.blockers


class TestGenerateRetro:
    def test_high_velocity(self) -> None:
        sprint = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            status=SprintStatus.ACTIVE,
            tasks=[
                SprintTask(
                    "S1-T1", "Done", "", "trading", TaskPriority.HIGH, TaskStatus.DONE
                ),
                SprintTask(
                    "S1-T2",
                    "Done",
                    "",
                    "research",
                    TaskPriority.MEDIUM,
                    TaskStatus.DONE,
                ),
            ],
        )
        retro = generate_retro(sprint, token_spend=5.0, pipeline_success_rate=98.0)
        assert retro.velocity == 2
        assert any(
            "velocity" in item.text.lower() or "completed" in item.text.lower()
            for item in retro.went_well
        )

    def test_low_velocity(self) -> None:
        sprint = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            tasks=[
                SprintTask(
                    "S1-T1", "Done", "", "trading", TaskPriority.HIGH, TaskStatus.DONE
                ),
                SprintTask(
                    "S1-T2",
                    "Todo",
                    "",
                    "research",
                    TaskPriority.MEDIUM,
                    TaskStatus.TODO,
                ),
                SprintTask(
                    "S1-T3", "Todo", "", "ops", TaskPriority.LOW, TaskStatus.TODO
                ),
                SprintTask(
                    "S1-T4", "Todo", "", "risk", TaskPriority.HIGH, TaskStatus.TODO
                ),
            ],
        )
        retro = generate_retro(sprint, pipeline_success_rate=95.0)
        assert retro.velocity == 1
        assert any("velocity" in item.text.lower() for item in retro.to_improve)

    def test_blocked_tasks_become_action_items(self) -> None:
        sprint = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            tasks=[
                SprintTask(
                    "S1-T1",
                    "Blocked task",
                    "",
                    "trading",
                    TaskPriority.HIGH,
                    TaskStatus.BLOCKED,
                ),
            ],
        )
        retro = generate_retro(sprint, pipeline_success_rate=95.0)
        assert len(retro.action_items) >= 1
        assert "Blocked task" in retro.action_items[0].text

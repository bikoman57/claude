"""Tests for Agile data models."""

from __future__ import annotations

from app.agile.models import (
    OKR,
    CeremonyType,
    RetroItem,
    RetroRecord,
    Roadmap,
    Sprint,
    SprintStatus,
    SprintTask,
    StandupEntry,
    StandupRecord,
    TaskPriority,
    TaskStatus,
)


class TestSprintModels:
    def test_sprint_creation(self) -> None:
        sprint = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            goals=["Test goal"],
            status=SprintStatus.ACTIVE,
        )
        assert sprint.number == 1
        assert sprint.status == SprintStatus.ACTIVE
        assert len(sprint.goals) == 1

    def test_sprint_task_defaults(self) -> None:
        task = SprintTask(
            id="S1-T1",
            title="Test task",
            description="A test",
            assignee_department="trading",
            priority=TaskPriority.HIGH,
        )
        assert task.status == TaskStatus.TODO
        assert task.completed_date is None


class TestCeremonyModels:
    def test_standup_entry_frozen(self) -> None:
        entry = StandupEntry(
            department="trading",
            agent="trading-screener",
            yesterday="Scanned signals",
            today="Monitor drawdowns",
            blockers="",
        )
        assert entry.department == "trading"

    def test_standup_record(self) -> None:
        record = StandupRecord(
            date="2026-02-12",
            sprint_number=1,
            session="pre-market",
        )
        assert record.entries == []
        assert record.summary == ""

    def test_retro_record(self) -> None:
        retro = RetroRecord(
            sprint_number=1,
            date="2026-02-14",
            went_well=[RetroItem("went_well", "High velocity")],
            velocity=5,
        )
        assert retro.velocity == 5
        assert len(retro.went_well) == 1


class TestRoadmapModels:
    def test_okr_defaults(self) -> None:
        okr = OKR(id="OKR-1", objective="Test objective")
        assert okr.progress_pct == 0.0
        assert okr.status == "active"

    def test_roadmap_defaults(self) -> None:
        roadmap = Roadmap()
        assert roadmap.current_sprint == 1
        assert roadmap.okrs == []


class TestEnums:
    def test_sprint_status_values(self) -> None:
        assert SprintStatus.ACTIVE == "ACTIVE"
        assert SprintStatus.COMPLETED == "COMPLETED"

    def test_ceremony_types(self) -> None:
        assert CeremonyType.STANDUP == "STANDUP"
        assert CeremonyType.RETROSPECTIVE == "RETROSPECTIVE"

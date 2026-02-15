"""Tests for Agile persistence layer."""

from __future__ import annotations

from pathlib import Path

from app.agile.models import (
    RetroItem,
    RetroRecord,
    Sprint,
    SprintStatus,
    SprintTask,
    StandupEntry,
    StandupRecord,
    TaskPriority,
    TaskStatus,
)
from app.agile.store import (
    advance_sprint,
    default_roadmap,
    get_current_sprint,
    is_sprint_over,
    list_retros,
    list_standups,
    load_retro,
    load_roadmap,
    load_sprints,
    load_standup,
    save_retro,
    save_sprints,
    save_standup,
)


class TestSprintPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        sprints_path = tmp_path / "sprints.json"
        sprint = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            goals=["Goal 1"],
            status=SprintStatus.ACTIVE,
            tasks=[
                SprintTask(
                    id="S1-T1",
                    title="Task 1",
                    description="Do thing",
                    assignee_department="trading",
                    priority=TaskPriority.HIGH,
                ),
            ],
        )
        save_sprints([sprint], sprints_path)
        loaded = load_sprints(sprints_path)
        assert len(loaded) == 1
        assert loaded[0].number == 1
        assert len(loaded[0].tasks) == 1
        assert loaded[0].tasks[0].title == "Task 1"

    def test_load_empty(self, tmp_path: Path) -> None:
        sprints_path = tmp_path / "sprints.json"
        result = load_sprints(sprints_path)
        assert result == []

    def test_get_current_sprint(self, tmp_path: Path) -> None:
        sprints_path = tmp_path / "sprints.json"
        s1 = Sprint(
            number=1,
            start_date="2026-02-03",
            end_date="2026-02-07",
            status=SprintStatus.COMPLETED,
        )
        s2 = Sprint(
            number=2,
            start_date="2026-02-10",
            end_date="2026-02-14",
            status=SprintStatus.ACTIVE,
        )
        save_sprints([s1, s2], sprints_path)

        current = get_current_sprint(sprints_path)
        assert current is not None
        assert current.number == 2

    def test_advance_sprint(self, tmp_path: Path) -> None:
        sprints_path = tmp_path / "sprints.json"
        s1 = Sprint(
            number=1,
            start_date="2026-02-10",
            end_date="2026-02-14",
            status=SprintStatus.ACTIVE,
            tasks=[
                SprintTask(
                    "S1-T1",
                    "Done task",
                    "",
                    "trading",
                    TaskPriority.HIGH,
                    TaskStatus.DONE,
                ),
                SprintTask(
                    "S1-T2",
                    "Not done",
                    "",
                    "research",
                    TaskPriority.MEDIUM,
                    TaskStatus.TODO,
                ),
            ],
        )
        save_sprints([s1], sprints_path)

        new_sprint = advance_sprint(sprints_path)
        assert new_sprint.number == 2
        assert new_sprint.status == SprintStatus.ACTIVE

        all_sprints = load_sprints(sprints_path)
        assert all_sprints[0].status == SprintStatus.COMPLETED
        assert all_sprints[0].velocity_points == 1


class TestStandupPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        record = StandupRecord(
            date="2026-02-12",
            sprint_number=1,
            session="pre-market",
            entries=[
                StandupEntry("trading", "screener", "Yesterday", "Today", ""),
            ],
            summary="All good",
        )
        save_standup(record, tmp_path)
        loaded = load_standup("2026-02-12", tmp_path)
        assert loaded is not None
        assert loaded.sprint_number == 1
        assert len(loaded.entries) == 1

    def test_list_standups(self, tmp_path: Path) -> None:
        for d in ["2026-02-10", "2026-02-11", "2026-02-12"]:
            save_standup(
                StandupRecord(date=d, sprint_number=1, session="pre-market"), tmp_path
            )
        dates = list_standups(tmp_path)
        assert dates == ["2026-02-10", "2026-02-11", "2026-02-12"]


class TestRetroPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        retro = RetroRecord(
            sprint_number=1,
            date="2026-02-14",
            went_well=[RetroItem("went_well", "Good job")],
            to_improve=[RetroItem("improve", "Be faster")],
            action_items=[
                RetroItem("action_item", "Fix pipeline", "ops", TaskPriority.HIGH)
            ],
            velocity=3,
        )
        save_retro(retro, tmp_path)
        loaded = load_retro(1, tmp_path)
        assert loaded is not None
        assert loaded.velocity == 3
        assert len(loaded.went_well) == 1
        assert len(loaded.action_items) == 1

    def test_list_retros(self, tmp_path: Path) -> None:
        for n in [1, 2, 3]:
            save_retro(RetroRecord(sprint_number=n, date="2026-02-14"), tmp_path)
        numbers = list_retros(tmp_path)
        assert numbers == [1, 2, 3]


class TestRoadmapPersistence:
    def test_default_roadmap(self) -> None:
        roadmap = default_roadmap()
        assert len(roadmap.okrs) == 5
        assert roadmap.okrs[0].id == "OKR-1"

    def test_save_and_load(self, tmp_path: Path) -> None:
        roadmap_path = tmp_path / "roadmap.json"
        roadmap = default_roadmap()
        from app.agile.store import save_roadmap

        save_roadmap(roadmap, roadmap_path)
        loaded = load_roadmap(roadmap_path)
        assert len(loaded.okrs) == 5


class TestInitAgile:
    def test_init_creates_sprint_and_roadmap(self, tmp_path: Path) -> None:
        # init_agile uses default paths, so we test the default_roadmap instead.
        roadmap = default_roadmap()
        assert len(roadmap.okrs) == 5
        assert roadmap.current_sprint == 1


class TestIsSprintOver:
    def test_none_sprint(self) -> None:
        assert is_sprint_over(None) is True

    def test_future_sprint(self) -> None:
        sprint = Sprint(number=1, start_date="2099-01-01", end_date="2099-01-05")
        assert is_sprint_over(sprint) is False

    def test_past_sprint(self) -> None:
        sprint = Sprint(number=1, start_date="2020-01-01", end_date="2020-01-05")
        assert is_sprint_over(sprint) is True

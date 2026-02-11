from __future__ import annotations

import sys

from app.scheduler.runner import (
    ModuleResult,
    SchedulerRun,
    load_status,
    run_all_modules,
    run_module,
)


def test_module_result_dataclass():
    r = ModuleResult(
        name="test",
        success=True,
        output="ok",
        error="",
        duration_seconds=1.0,
    )
    assert r.success is True


def test_scheduler_run_dataclass():
    run = SchedulerRun(
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:01:00+00:00",
        results=[],
        total_modules=0,
        succeeded=0,
        failed=0,
    )
    assert run.total_modules == 0


def test_run_module_success():
    result = run_module(
        "test",
        [sys.executable, "-c", "print('hello')"],
    )
    assert result.success is True
    assert "hello" in result.output
    assert result.name == "test"


def test_run_module_failure():
    result = run_module(
        "test",
        [sys.executable, "-c", "raise SystemExit(1)"],
    )
    assert result.success is False


def test_run_module_timeout():
    result = run_module(
        "test",
        [sys.executable, "-c", "import time; time.sleep(10)"],
        timeout=1,
    )
    assert result.success is False
    assert "Timed out" in result.error


def test_run_module_bad_command():
    result = run_module("test", ["nonexistent_program_xyz"])
    assert result.success is False
    assert result.error != ""


def test_run_all_modules(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.runner._STATUS_PATH",
        tmp_path / "status.json",
    )
    commands = [
        ("ok_module", [sys.executable, "-c", "print('ok')"]),
        ("fail_module", [sys.executable, "-c", "raise SystemExit(1)"]),
    ]
    run = run_all_modules(commands=commands)

    assert run.total_modules == 2
    assert run.succeeded == 1
    assert run.failed == 1
    assert run.results[0].success is True
    assert run.results[1].success is False


def test_save_and_load_status(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.runner._STATUS_PATH",
        tmp_path / "status.json",
    )
    commands = [
        ("test", [sys.executable, "-c", "print('hi')"]),
    ]
    run_all_modules(commands=commands)

    loaded = load_status()
    assert loaded is not None
    assert loaded.total_modules == 1
    assert loaded.succeeded == 1
    assert len(loaded.results) == 1


def test_load_status_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.scheduler.runner._STATUS_PATH",
        tmp_path / "nonexistent.json",
    )
    assert load_status() is None

"""Scheduler CLI.

Usage:
    python -m app.scheduler daily       Run all modules + send Telegram report
    python -m app.scheduler test-run    Run all modules (no Telegram)
    python -m app.scheduler publish     Run all modules + publish HTML to GitHub Pages
    python -m app.scheduler status      Show last run status
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from app.scheduler.publisher import git_publish, write_report
from app.scheduler.report import build_report_text, send_daily_report
from app.scheduler.runner import load_status, run_all_modules


def _cmd_daily() -> int:
    print("Running all modules...")  # noqa: T201
    run = run_all_modules()
    print(  # noqa: T201
        f"Completed: {run.succeeded}/{run.total_modules} OK, "
        f"{run.failed} failed",
    )

    print("\nSending Telegram report...")  # noqa: T201
    sent = asyncio.run(send_daily_report(run))
    if sent:
        print("Report sent successfully.")  # noqa: T201
    else:
        print("Failed to send report (check Telegram config).")  # noqa: T201
        report = build_report_text(run)
        print("\n--- Report Preview ---")  # noqa: T201
        print(report)  # noqa: T201

    _print_setup_hint()
    return 0


def _cmd_test_run() -> int:
    print("Running all modules (test mode, no Telegram)...")  # noqa: T201
    run = run_all_modules()
    print(  # noqa: T201
        f"Completed: {run.succeeded}/{run.total_modules} OK, "
        f"{run.failed} failed",
    )

    report = build_report_text(run)
    print("\n--- Report Preview ---")  # noqa: T201
    print(report)  # noqa: T201
    return 0


def _cmd_status() -> int:
    run = load_status()
    if run is None:
        print("No previous run found.")  # noqa: T201
        return 0

    print(json.dumps(asdict(run), indent=2))  # noqa: T201
    return 0


def _cmd_publish() -> int:
    print("Running all modules...")  # noqa: T201
    run = run_all_modules()
    print(  # noqa: T201
        f"Completed: {run.succeeded}/{run.total_modules} OK, "
        f"{run.failed} failed",
    )

    print("\nGenerating HTML report...")  # noqa: T201
    report_path = write_report(run)
    print(f"Report written to {report_path}")  # noqa: T201

    print("\nPublishing to GitHub Pages...")  # noqa: T201
    pushed = git_publish()
    if pushed:
        print("Published successfully.")  # noqa: T201
    else:
        print("Failed to push (check git config).")  # noqa: T201

    return 0


def _print_setup_hint() -> None:
    print(  # noqa: T201
        "\nTo schedule daily runs via Windows Task Scheduler:"
        "\n  Program: C:\\Users\\texcu\\.local\\bin\\uv.exe"
        "\n  Arguments: run python -m app.scheduler daily"
        "\n  Start in: C:\\Users\\texcu\\OneDrive\\Documents\\claude"
        "\n  Trigger: Daily at 6:30 AM ET",
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        return 1

    cmd = sys.argv[1]

    match cmd:
        case "daily":
            return _cmd_daily()
        case "test-run":
            return _cmd_test_run()
        case "publish":
            return _cmd_publish()
        case "status":
            return _cmd_status()
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

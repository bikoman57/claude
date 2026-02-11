"""Scheduler CLI.

Usage:
    python -m app.scheduler daily        Run all modules + send Telegram report
    python -m app.scheduler test-run     Run all modules (no Telegram)
    python -m app.scheduler publish      Run all modules + publish HTML to GitHub Pages
    python -m app.scheduler pre-market   Full pre-market scheduled run
    python -m app.scheduler post-market  Full post-market scheduled run
    python -m app.scheduler status       Show last run status
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from app.scheduler.publisher import git_publish, write_report
from app.scheduler.report import build_report_text, send_daily_report
from app.scheduler.runner import load_status, run_all_modules
from app.scheduler.scheduled_run import RunSession, run_scheduled


def _cmd_daily() -> int:
    print("Running all modules...")  # noqa: T201
    run = run_all_modules()
    print(  # noqa: T201
        f"Completed: {run.succeeded}/{run.total_modules} OK, {run.failed} failed",
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
        f"Completed: {run.succeeded}/{run.total_modules} OK, {run.failed} failed",
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
        f"Completed: {run.succeeded}/{run.total_modules} OK, {run.failed} failed",
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


def _cmd_pre_market() -> int:
    """Run full pre-market analysis."""
    print("Starting pre-market scheduled run...")  # noqa: T201
    result = run_scheduled(RunSession.PRE_MARKET)
    ok = result.pipeline_modules_ok
    total = result.pipeline_modules_total
    pub = "OK" if result.publish_success else "FAIL"
    cl = "OK" if result.claude_success else "FAIL"
    tg = "OK" if result.telegram_success else "FAIL"
    print(  # noqa: T201
        f"Pre-market complete: pipeline {ok}/{total}, "
        f"publish={pub}, claude={cl}, telegram={tg}",
    )
    return 0 if result.claude_success else 1


def _cmd_post_market() -> int:
    """Run full post-market analysis."""
    print("Starting post-market scheduled run...")  # noqa: T201
    result = run_scheduled(RunSession.POST_MARKET)
    ok = result.pipeline_modules_ok
    total = result.pipeline_modules_total
    pub = "OK" if result.publish_success else "FAIL"
    cl = "OK" if result.claude_success else "FAIL"
    tg = "OK" if result.telegram_success else "FAIL"
    print(  # noqa: T201
        f"Post-market complete: pipeline {ok}/{total}, "
        f"publish={pub}, claude={cl}, telegram={tg}",
    )
    return 0 if result.claude_success else 1


def _print_setup_hint() -> None:
    print(  # noqa: T201
        "\nTo set up scheduled tasks, run as Administrator:"
        "\n  powershell -ExecutionPolicy Bypass"
        " -File scripts\\setup-scheduled-tasks.ps1"
        "\n"
        "\nTasks created:"
        "\n  FinAgents-PreMarket:  Weekdays 7:00 AM ET"
        "\n  FinAgents-PostMarket: Weekdays 4:30 PM ET",
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
        case "pre-market":
            return _cmd_pre_market()
        case "post-market":
            return _cmd_post_market()
        case "status":
            return _cmd_status()
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

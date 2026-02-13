"""Scheduler CLI.

Usage:
    python -m app.scheduler daily        Run all modules + send Telegram report
    python -m app.scheduler test-run     Run all modules (no Telegram)
    python -m app.scheduler publish      Run all modules + publish HTML to GitHub Pages
    python -m app.scheduler pre-market   Full pre-market scheduled run
    python -m app.scheduler post-market  Full post-market scheduled run
    python -m app.scheduler status       Show last run status
    python -m app.scheduler ceremonies   Show today's ceremony schedule
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime

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


def _cmd_ceremonies() -> int:
    """Show today's ceremony schedule."""
    today = datetime.now(tz=UTC).date()
    day_name = today.strftime("%A")
    is_monday = today.weekday() == 0
    is_friday = today.weekday() == 4

    print(f"=== Ceremony Schedule for {today.isoformat()} ({day_name}) ===")  # noqa: T201
    print()  # noqa: T201
    print("Pre-Market (7:00 AM ET):")  # noqa: T201
    if is_monday:
        print("  [0a] Sprint Planning — create/advance sprint, assign tasks")  # noqa: T201
    print("  [0]  Daily Standup — department status, blockers")  # noqa: T201
    print("  [1]  Data Pipeline — run all modules")  # noqa: T201
    print("  [2]  Publish HTML Report")  # noqa: T201
    print("  [3]  Claude Analysis")  # noqa: T201
    print("  [4]  Telegram Summary")  # noqa: T201
    print("  [5]  Record token usage + pipeline health")  # noqa: T201
    print()  # noqa: T201
    print("Post-Market (4:30 PM ET):")  # noqa: T201
    print("  [1]  Data Pipeline — run all modules")  # noqa: T201
    print("  [2]  Publish HTML Report")  # noqa: T201
    print("  [3]  Claude Analysis")  # noqa: T201
    print("  [4]  Telegram Summary")  # noqa: T201
    print("  [5]  Record token usage + pipeline health")  # noqa: T201
    print("  [6]  Postmortem detection")  # noqa: T201
    if is_friday:
        print("  [7]  Sprint Review — accomplishments vs goals")  # noqa: T201
        print("  [8]  Sprint Retrospective — went well / improve / action items")  # noqa: T201
        print("  [9]  Auto-advance sprint")  # noqa: T201
    return 0


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
        case "ceremonies":
            return _cmd_ceremonies()
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

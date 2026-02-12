"""Scheduled run orchestration: pipeline -> publish -> Claude analysis -> Telegram."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

from app.scheduler.config import SchedulerConfig
from app.scheduler.publisher import git_publish, write_report
from app.scheduler.runner import SchedulerRun, run_all_modules
from app.telegram.client import TelegramClient
from app.telegram.config import TelegramConfig
from app.telegram.dispatcher import split_message
from app.telegram.formatting import bold, escape_markdown

logger = logging.getLogger(__name__)

_ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

# Tools to pre-approve for headless Claude CLI runs.
# These match the project .claude/settings.json allow-list so that
# scheduled and Telegram-triggered runs execute without permission prompts.
_ALLOWED_TOOLS: list[str] = [
    "Bash(uv run*)",
    "Bash(uv sync*)",
    "Bash(git *)",
    "Bash(gh *)",
    "Bash(powershell*)",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "TodoWrite",
    "Task",
]


class RunSession(StrEnum):
    """Which scheduled session this is."""

    PRE_MARKET = "pre-market"
    POST_MARKET = "post-market"


# ---------------------------------------------------------------------------
# Claude analysis prompts
# ---------------------------------------------------------------------------

_PRE_MARKET_PROMPT = """\
You are running the pre-market analysis for {date}. US markets open at 9:30 AM ET.

## Priority: Prepare for Today's Trading Session

1. **Scan current signals**: Run `uv run python -m app.etf signals` and \
`uv run python -m app.etf active` to see the current state of all tracked ETFs.

2. **Review overnight developments**: Check international markets, futures, \
and pre-market movers. What changed since yesterday's close?

3. **Full data pipeline**: Run the /unified-report skill to collect all market \
data across every domain (macro, yields, news, geopolitical, social, statistics).

4. **Assess entry signals**: For ETFs in SIGNAL or ALERT state, assess \
whether today is a good entry day. Consider:
   - Economic data releases scheduled today
   - FOMC or Fed speaker calendar
   - Earnings reports that could move sectors
   - Geopolitical developments overnight

5. **Strategy research (spend at least 30 minutes here)**:
   - Run `uv run python -m app.strategy proposals` and analyze the results
   - Run `uv run python -m app.strategy optimize` for any ETFs close to entry
   - Look for new ETF opportunities beyond the current universe
   - Research any sector rotation patterns emerging
   - Check if VIX term structure suggests volatility opportunities
   - Review correlation breakdowns between indices

6. **Actionable summary**: End with specific recommendations for today:
   - Which signals to watch most closely
   - Price levels that would trigger entries
   - Risk factors to monitor during the session
   - Confidence scores for each potential trade

Send a Telegram summary of key findings when done using: \
`uv run python -m app.telegram notify "your summary here"`
"""

_POST_MARKET_PROMPT = """\
You are running the post-market analysis for {date}. US markets closed at 4:00 PM ET.

## Priority: Review Today and Position for Tomorrow

1. **Scan updated signals**: Run `uv run python -m app.etf signals` and \
`uv run python -m app.etf active` to see end-of-day signal states.

2. **Full data pipeline**: Run the /unified-report skill to collect all \
end-of-day data across every domain.

3. **Daily performance review**: How did the market close? Compare to \
this morning's pre-market expectations. Which sectors outperformed/underperformed?

4. **Position updates**: For any ACTIVE positions, calculate updated P&L. \
Did any reach profit targets today? Run `uv run python -m app.history summary`.

5. **Signal state changes**: Which ETFs moved between states today? \
Any new ALERT or SIGNAL states? Any that dropped back to WATCH? \
Are drawdowns deepening or recovering?

6. **Strategy deep-dive (spend at least 30 minutes here)**:
   - Run `uv run python -m app.strategy backtest` with different parameters
   - Run `uv run python -m app.strategy optimize` for all tracked ETFs
   - Run `uv run python -m app.strategy proposals` and compare to morning
   - Analyze whether today's moves suggest new entry/exit thresholds
   - Research whether today's sector moves suggest rotation opportunities
   - Check news sentiment shift from morning to close
   - Look for end-of-day anomalies (options expiration effects, rebalancing)

7. **Overnight positioning summary**: End with:
   - Key levels to watch in after-hours / overnight futures
   - Economic calendar for tomorrow
   - What would change your current thesis
   - Updated confidence scores for all signals

Publish the HTML report: `uv run python -m app.scheduler publish`

Send a Telegram summary of key findings when done using: \
`uv run python -m app.telegram notify "your summary here"`
"""


@dataclass
class ScheduledRunResult:
    """Result of a complete scheduled run."""

    session: RunSession
    started_at: str
    finished_at: str
    pipeline_success: bool
    pipeline_modules_ok: int
    pipeline_modules_total: int
    publish_success: bool
    claude_success: bool
    claude_output: str
    telegram_success: bool


def _setup_logging(config: SchedulerConfig, session: RunSession) -> Path:
    """Configure file logging for this run. Returns log file path."""
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    log_file = config.logs_dir / f"{date_str}_{session.value}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"),
    )
    root_logger.addHandler(console)

    return log_file


def _run_pipeline() -> SchedulerRun:
    """Phase 1: Run all data collection modules."""
    logger.info("Phase 1: Running data pipeline (%d modules)...", 15)
    run = run_all_modules(timeout=120)
    logger.info(
        "Pipeline complete: %d/%d succeeded, %d failed",
        run.succeeded,
        run.total_modules,
        run.failed,
    )
    for result in run.results:
        if not result.success:
            logger.warning("Module %s failed: %s", result.name, result.error[:200])
    return run


def _publish_report(run: SchedulerRun) -> bool:
    """Phase 2: Generate HTML report and push to GitHub Pages."""
    logger.info("Phase 2: Publishing HTML report...")
    try:
        report_path = write_report(run)
        logger.info("HTML report written to %s", report_path)
        pushed = git_publish()
        if pushed:
            logger.info("Report pushed to GitHub Pages")
        else:
            logger.warning("Git push failed (non-fatal)")
        return pushed
    except Exception:
        logger.exception("Error during report publishing")
        return False


def _build_allowed_tools_args() -> list[str]:
    """Build --allowedTools CLI arguments for Claude headless mode."""
    args: list[str] = []
    for tool in _ALLOWED_TOOLS:
        args.extend(["--allowedTools", tool])
    return args


def _run_claude_analysis(
    config: SchedulerConfig,
    session: RunSession,
) -> tuple[bool, str]:
    """Phase 3: Invoke Claude CLI for comprehensive agent analysis."""
    date_str = datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")

    prompt = (
        _PRE_MARKET_PROMPT.format(date=date_str)
        if session == RunSession.PRE_MARKET
        else _POST_MARKET_PROMPT.format(date=date_str)
    )

    logger.info(
        "Phase 3: Starting Claude %s analysis (timeout: %ds)...",
        session.value,
        config.claude_timeout,
    )

    try:
        env = os.environ.copy()
        env.setdefault("CLAUDE_CODE_GIT_BASH_PATH", r"D:\Git\bin\bash.exe")

        cmd = [str(config.claude_executable), "-p", prompt, "--verbose"]
        cmd.extend(_build_allowed_tools_args())

        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=config.claude_timeout,
            cwd=str(config.project_dir),
            env=env,
        )

        output = result.stdout.strip()
        if result.returncode != 0:
            stderr = result.stderr.strip()
            logger.warning(
                "Claude exited with code %d. stderr: %s",
                result.returncode,
                stderr[:500],
            )
            return False, output or stderr or "(no output)"

        logger.info("Claude analysis complete (%d chars output)", len(output))
        return True, output

    except subprocess.TimeoutExpired:
        logger.error("Claude analysis timed out after %ds", config.claude_timeout)
        return False, f"Timed out after {config.claude_timeout}s"

    except FileNotFoundError:
        logger.error("Claude CLI not found at: %s", config.claude_executable)
        return False, f"Claude CLI not found: {config.claude_executable}"

    except Exception as exc:
        logger.exception("Unexpected error running Claude CLI")
        return False, str(exc)


async def _send_telegram_summary(
    run: SchedulerRun,
    session: RunSession,
    claude_output: str,
    *,
    claude_success: bool,
) -> bool:
    """Phase 4: Send Telegram summary combining pipeline + Claude results."""
    logger.info("Phase 4: Sending Telegram summary...")
    try:
        tg_config = TelegramConfig.from_env()
    except ValueError:
        logger.warning("Telegram not configured, skipping notification")
        return False

    date_str = datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")
    session_label = session.value.upper().replace("-", " ")

    lines = [
        bold(f"{escape_markdown(session_label)} REPORT — {escape_markdown(date_str)}"),
        "",
        escape_markdown(
            f"Pipeline: {run.succeeded}/{run.total_modules} modules OK",
        ),
    ]

    if not claude_success:
        lines.append("")
        lines.append(escape_markdown("Claude analysis failed or timed out."))

    try:
        async with TelegramClient(tg_config) as client:
            await client.send_message("\n".join(lines))
            if claude_success and claude_output:
                chunks = split_message(claude_output)
                for chunk in chunks[:5]:
                    await client.send_message(chunk, parse_mode="")
        logger.info("Telegram summary sent")
    except Exception:
        logger.exception("Failed to send Telegram summary")
        return False
    else:
        return True


def run_scheduled(session: RunSession) -> ScheduledRunResult:
    """Execute a complete scheduled run.

    Phases: pipeline -> publish -> Claude analysis -> Telegram.
    Each phase is independent — failure in one does not block the next.
    """
    config = SchedulerConfig.from_env()
    log_file = _setup_logging(config, session)

    started = datetime.now(tz=_ISRAEL_TZ).isoformat(timespec="seconds")
    logger.info("=" * 60)
    logger.info("SCHEDULED RUN: %s at %s", session.value, started)
    logger.info("Log file: %s", log_file)
    logger.info("=" * 60)

    # Phase 1: Data pipeline
    pipeline_run = _run_pipeline()

    # Phase 2: Publish HTML report
    publish_ok = _publish_report(pipeline_run)

    # Phase 3: Claude analysis (the main time sink, up to 1 hour)
    claude_ok, claude_output = _run_claude_analysis(config, session)

    # Phase 4: Telegram summary
    telegram_ok = asyncio.run(
        _send_telegram_summary(
            pipeline_run,
            session,
            claude_output,
            claude_success=claude_ok,
        ),
    )

    finished = datetime.now(tz=_ISRAEL_TZ).isoformat(timespec="seconds")
    logger.info("=" * 60)
    logger.info("SCHEDULED RUN COMPLETE: %s", finished)
    logger.info(
        "Pipeline: %d/%d | Publish: %s | Claude: %s | Telegram: %s",
        pipeline_run.succeeded,
        pipeline_run.total_modules,
        "OK" if publish_ok else "FAIL",
        "OK" if claude_ok else "FAIL",
        "OK" if telegram_ok else "FAIL",
    )
    logger.info("=" * 60)

    return ScheduledRunResult(
        session=session,
        started_at=started,
        finished_at=finished,
        pipeline_success=pipeline_run.failed == 0,
        pipeline_modules_ok=pipeline_run.succeeded,
        pipeline_modules_total=pipeline_run.total_modules,
        publish_success=publish_ok,
        claude_success=claude_ok,
        claude_output=claude_output[:10000],
        telegram_success=telegram_ok,
    )

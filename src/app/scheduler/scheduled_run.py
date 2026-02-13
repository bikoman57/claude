"""Scheduled run orchestration.

Phases: ceremonies -> pipeline -> publish -> Claude -> Telegram -> tracking.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
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


def _build_pipeline_summary(run: SchedulerRun) -> str:
    """Build a brief summary of pipeline module results for the Claude prompt."""
    lines: list[str] = []
    for result in run.results:
        status = "OK" if result.success else "FAIL"
        chars = len(result.output) if result.output else 0
        dur = f"{result.duration_seconds:.1f}s"
        line = f"  - {result.name}: {status} ({chars:,} chars, {dur})"
        if not result.success and result.error:
            line += f" — {result.error[:100]}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cross-run continuity helpers
# ---------------------------------------------------------------------------


def _claude_log_sort_key(path: Path) -> str:
    """Convert Claude log filename to a chronologically sortable key.

    pre-market runs before post-market on the same day, but
    alphabetically "post" < "pre", so we map to numeric order.
    """
    name = path.stem
    if "_pre-market_" in name:
        return name[:10] + "_0"
    if "_post-market_" in name:
        return name[:10] + "_1"
    return name


def _find_previous_claude_log(
    session: RunSession,
    logs_dir: Path,
    date_now: datetime,
) -> Path | None:
    """Find the most recent Claude analysis log before this run."""
    if not logs_dir.exists():
        return None

    current_key = date_now.strftime("%Y-%m-%d") + (
        "_0" if session == RunSession.PRE_MARKET else "_1"
    )

    candidates = sorted(
        logs_dir.glob("*_claude.log"),
        key=_claude_log_sort_key,
    )

    previous = [
        p
        for p in candidates
        if _claude_log_sort_key(p) < current_key
        and p.stat().st_size > 0
    ]

    return previous[-1] if previous else None


def _continuity_previous_analysis(
    session: RunSession,
    config: SchedulerConfig,
    date_now: datetime,
) -> list[str]:
    """Summarize the most recent Claude analysis log."""
    try:
        prev_log = _find_previous_claude_log(
            session, config.logs_dir, date_now,
        )
        if prev_log is None:
            return []
        content = prev_log.read_text(
            encoding="utf-8", errors="replace",
        )
        if len(content) < 50:
            return []
        head = content[:2000]
        tail = content[-1000:] if len(content) > 3000 else ""
        label = prev_log.stem
        parts = [f"### Previous Analysis ({label})\n```\n{head}\n```"]
        if tail:
            parts.append(
                f"\n... ({len(content):,} chars total) ...\n"
                f"\n```\n{tail}\n```"
            )
        return ["\n".join(parts)]
    except Exception:
        logger.debug("Could not load previous analysis", exc_info=True)
        return []


def _continuity_sprint() -> list[str]:
    """Summarize current sprint state."""
    try:
        from app.agile.store import get_current_sprint

        sprint = get_current_sprint()
        if sprint is None:
            return []
        total = len(sprint.tasks)
        done = sum(1 for t in sprint.tasks if t.status.value == "DONE")
        in_prog = sum(
            1 for t in sprint.tasks if t.status.value == "IN_PROGRESS"
        )
        blocked = sum(
            1 for t in sprint.tasks if t.status.value == "BLOCKED"
        )
        goals_str = ", ".join(sprint.goals) if sprint.goals else "none"
        lines = [
            f"### Sprint {sprint.number}"
            f" ({sprint.start_date} to {sprint.end_date})",
            f"- Tasks: {done}/{total} done,"
            f" {in_prog} in-progress, {blocked} blocked",
            f"- Goals: {goals_str}",
        ]
        return ["\n".join(lines)]
    except Exception:
        logger.debug("Could not load sprint state", exc_info=True)
        return []


def _continuity_standup(today_str: str) -> list[str]:
    """Summarize today's standup record."""
    try:
        from app.agile.store import load_standup

        standup = load_standup(today_str)
        if standup is None:
            return []
        lines = [f"### Standup ({today_str})"]
        if standup.summary:
            lines.append(f"Summary: {standup.summary}")
        for entry in standup.entries[:5]:
            blocker = (
                f" [BLOCKED: {entry.blockers}]" if entry.blockers else ""
            )
            lines.append(f"- {entry.department}: {entry.today}{blocker}")
        return ["\n".join(lines)]
    except Exception:
        logger.debug("Could not load standup", exc_info=True)
        return []


def _continuity_signals(config: SchedulerConfig) -> list[str]:
    """Summarize current signal states from signals.json."""
    try:
        import json

        signals_path = config.project_dir / "data" / "signals.json"
        if not signals_path.exists():
            return []
        raw = json.loads(signals_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list) or not raw:
            return []
        lines = ["### Signal States"]
        for sig in raw:
            ticker = sig.get("leveraged_ticker", "?")
            state = sig.get("state", "?")
            dd = sig.get("underlying_drawdown_pct", 0)
            dd_str = f"{abs(dd) * 100:.1f}%"
            pl = sig.get("current_pl_pct")
            extra = f", P&L: {pl:+.1%}" if pl is not None else ""
            lines.append(f"- {ticker}: {state} (drawdown {dd_str}{extra})")
        return ["\n".join(lines)]
    except Exception:
        logger.debug("Could not load signals", exc_info=True)
        return []


def _continuity_forecast_accuracy(config: SchedulerConfig) -> list[str]:
    """Summarize forecast accuracy metrics."""
    try:
        import json

        path = config.project_dir / "data" / "forecast_accuracy.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        hit = raw.get("hit_rate", 0)
        recent = raw.get("recent_hit_rate", 0)
        trend = raw.get("trend", "UNKNOWN")
        total = raw.get("total_verifications", 0)
        lines = [
            "### Forecast Accuracy",
            f"- Overall: {hit:.0%} ({total} verifications)",
            f"- Recent: {recent:.0%}, trend: {trend}",
        ]
        return ["\n".join(lines)]
    except Exception:
        logger.debug("Could not load forecast accuracy", exc_info=True)
        return []


def _build_continuity_context(
    session: RunSession,
    config: SchedulerConfig,
) -> str:
    """Gather cross-run continuity data for the Claude prompt.

    Each data source is independently guarded so missing data
    never crashes the scheduled run.
    """
    date_now = datetime.now(tz=_ISRAEL_TZ)
    today_str = date_now.strftime("%Y-%m-%d")

    sections: list[str] = []
    sections.extend(_continuity_previous_analysis(session, config, date_now))
    sections.extend(_continuity_sprint())
    sections.extend(_continuity_standup(today_str))
    sections.extend(_continuity_signals(config))
    sections.extend(_continuity_forecast_accuracy(config))

    if not sections:
        return ""
    return "## Cross-Run Continuity Context\n\n" + "\n\n".join(sections) + "\n\n"


# ---------------------------------------------------------------------------
# Claude analysis prompts
# ---------------------------------------------------------------------------

_PRE_MARKET_PROMPT = """\
You are running the pre-market analysis for {date}. US markets open at 9:30 AM ET.

## TIME BUDGET: Complete ALL analysis within 30 minutes. Prioritize actionable insights.

## Data Already Collected

The data pipeline just ran ({pipeline_ok}/{pipeline_total} modules OK).
All module outputs are saved in `data/scheduler_status.json` — read this file to get
every module's full output. DO NOT re-run data collection commands.

Module summary:
{pipeline_summary}

{continuity_context}\
## Your Analysis Tasks

1. **Read pipeline data**: Read `data/scheduler_status.json`. Parse the JSON and
   extract each module's `output` field. This has all signals, macro data, SEC
   filings, news, geopolitical events, social sentiment, statistics, strategy
   proposals, forecasts, risk, portfolio, and quant data.

2. **Quick market snapshot**:
   ```bash
   uv run python -c "
   import yfinance as yf
   tickers = [('SPY','S&P 500'),('QQQ','Nasdaq-100'),
              ('IWM','Russell 2000'),('^VIX','VIX')]
   for sym, name in tickers:
       t = yf.Ticker(sym)
       h = t.history(period='5d')
       if len(h) >= 2:
           chg = (h['Close'].iloc[-1] / h['Close'].iloc[-2] - 1) * 100
           print(f'{{name}}: {{h[\"Close\"].iloc[-1]:.2f}} ({{chg:+.2f}}%)')
   "
   ```

3. **Cross-reference domains**: Identify tensions and confirming signals across
   macro, technical, geopolitical, social, and news data. Flag contradictions.

4. **Assess entry signals**: For ETFs in SIGNAL or ALERT state, compute
   confidence scores using all 12 factors. Note specific entry price levels.

5. **Strategy insights**: From the strategy.proposals, strategy.forecast, and
   strategy.verify pipeline outputs, summarize top strategies and parameter
   adjustments suggested by backtests.

6. **Actionable summary**: End with:
   - Top signals ranked by confidence
   - Specific entry price levels
   - Key risks and catalysts for today
   - What would change your thesis

Send a Telegram summary of key findings when done using: \
`uv run python -m app.telegram notify "your summary here"`
"""

_POST_MARKET_PROMPT = """\
You are running the post-market analysis for {date}. US markets closed at 4:00 PM ET.

## TIME BUDGET: Complete ALL analysis within 30 minutes. Prioritize actionable insights.

## Data Already Collected

The data pipeline just ran ({pipeline_ok}/{pipeline_total} modules OK).
All module outputs are saved in `data/scheduler_status.json` — read this file to get
every module's full output. DO NOT re-run data collection commands.

Module summary:
{pipeline_summary}

{continuity_context}\
## Your Analysis Tasks

1. **Read pipeline data**: Read `data/scheduler_status.json`. Parse the JSON and
   extract each module's `output` field.

2. **Daily performance review**: How did the market close? Which sectors
   outperformed/underperformed? Compare to recent trends.

3. **Signal state changes**: Which ETFs moved between states today? New ALERTs
   or SIGNALs? Any dropping back to WATCH? Are drawdowns deepening or recovering?

4. **Position updates**: For ACTIVE positions, calculate updated P&L from the
   pipeline data. Did any reach profit targets? Check history.summary output.

5. **Strategy review**: From the strategy.proposals, strategy.backtest-all, and
   strategy.forecast pipeline outputs, identify:
   - Best/worst performing strategies
   - Parameter adjustments suggested by backtests
   - Emerging sector rotation opportunities

6. **Overnight positioning**: End with:
   - Key levels to watch in after-hours / overnight futures
   - Tomorrow's economic calendar and earnings
   - What would change your current thesis
   - Updated confidence scores for all signals

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
    pipeline_run: SchedulerRun,
) -> tuple[bool, str, str, float]:
    """Phase 3: Invoke Claude CLI for comprehensive agent analysis.

    Output is streamed to log files so partial results survive timeouts.
    Returns (success, stdout, stderr, duration_seconds).
    """
    date_str = datetime.now(tz=_ISRAEL_TZ).strftime("%Y-%m-%d")

    pipeline_summary = _build_pipeline_summary(pipeline_run)
    continuity = _build_continuity_context(session, config)
    prompt_template = (
        _PRE_MARKET_PROMPT
        if session == RunSession.PRE_MARKET
        else _POST_MARKET_PROMPT
    )
    prompt = prompt_template.format(
        date=date_str,
        pipeline_ok=pipeline_run.succeeded,
        pipeline_total=pipeline_run.total_modules,
        pipeline_summary=pipeline_summary,
        continuity_context=continuity,
    )

    logger.info(
        "Phase 3: Starting Claude %s analysis (timeout: %ds)...",
        session.value,
        config.claude_timeout,
    )

    # Log files for Claude output — streamed in real-time so nothing is lost.
    claude_stdout_log = config.logs_dir / f"{date_str}_{session.value}_claude.log"
    claude_stderr_log = (
        config.logs_dir / f"{date_str}_{session.value}_claude_verbose.log"
    )

    start_time = time.monotonic()

    try:
        env = os.environ.copy()
        env.setdefault("CLAUDE_CODE_GIT_BASH_PATH", r"D:\Git\bin\bash.exe")

        cmd = [str(config.claude_executable), "-p", prompt, "--verbose"]
        cmd.extend(_build_allowed_tools_args())

        timed_out = False

        # Stream stdout/stderr to files so partial output survives timeouts.
        with (
            claude_stdout_log.open("wb") as f_out,
            claude_stderr_log.open("wb") as f_err,
        ):
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdout=f_out,
                stderr=f_err,
                cwd=str(config.project_dir),
                env=env,
            )
            try:
                proc.wait(timeout=config.claude_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                timed_out = True

        duration = time.monotonic() - start_time

        # Read captured output (files are closed by the with-block).
        output = claude_stdout_log.read_text(
            encoding="utf-8", errors="replace"
        ).strip()
        stderr = claude_stderr_log.read_text(
            encoding="utf-8", errors="replace"
        ).strip()

        if timed_out:
            logger.error(
                "Claude analysis timed out after %ds", config.claude_timeout
            )
            logger.info(
                "Partial output saved to %s (%d chars)",
                claude_stdout_log,
                len(output),
            )
            fallback = f"Timed out after {config.claude_timeout}s"
            return False, output or fallback, stderr, duration

        if proc.returncode != 0:
            logger.warning(
                "Claude exited with code %d. stderr: %s",
                proc.returncode,
                stderr[:500],
            )
            return False, output or stderr or "(no output)", stderr, duration

        logger.info(
            "Claude analysis complete (%d chars output, saved to %s)",
            len(output),
            claude_stdout_log,
        )
        return True, output, stderr, duration

    except FileNotFoundError:
        duration = time.monotonic() - start_time
        logger.error("Claude CLI not found at: %s", config.claude_executable)
        return False, f"Claude CLI not found: {config.claude_executable}", "", duration

    except Exception as exc:
        duration = time.monotonic() - start_time
        logger.exception("Unexpected error running Claude CLI")
        return False, str(exc), "", duration


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

    has_partial_output = bool(claude_output and len(claude_output) > 100)

    lines = [
        bold(f"{escape_markdown(session_label)} REPORT — {escape_markdown(date_str)}"),
        "",
        escape_markdown(
            f"Pipeline: {run.succeeded}/{run.total_modules} modules OK",
        ),
    ]

    if not claude_success:
        lines.append("")
        if has_partial_output:
            lines.append(
                escape_markdown("Claude analysis timed out (partial results below)."),
            )
        else:
            lines.append(escape_markdown("Claude analysis failed or timed out."))

    try:
        async with TelegramClient(tg_config) as client:
            await client.send_message("\n".join(lines))
            # Send output if available — even partial output from timeouts.
            if has_partial_output or (claude_success and claude_output):
                chunks = split_message(claude_output)
                for chunk in chunks[:5]:
                    await client.send_message(chunk, parse_mode="")
        logger.info("Telegram summary sent")
    except Exception:
        logger.exception("Failed to send Telegram summary")
        return False
    else:
        return True


def _run_ceremonies_pre(session: RunSession) -> None:
    """Phase 0: Run pre-analysis ceremonies (standup, Monday planning)."""
    from app.agile.ceremonies import generate_planning, generate_standup
    from app.agile.store import (
        advance_sprint,
        get_current_sprint,
        is_sprint_over,
        load_sprints,
        save_sprints,
    )

    today = datetime.now(tz=UTC).date()
    is_monday = today.weekday() == 0

    try:
        current = get_current_sprint()

        # Auto-create/advance sprint if needed.
        if current is None or is_sprint_over(current):
            logger.info("Phase 0a: Sprint planning (auto-advancing)...")
            previous = current
            current = advance_sprint()
            if previous:
                tasks = generate_planning(previous)
                current.tasks.extend(tasks)
                # Re-number tasks for new sprint.
                for i, task in enumerate(current.tasks, 1):
                    task.id = f"S{current.number}-T{i}"
                sprints = load_sprints()
                save_sprints(sprints)
            logger.info(
                "Sprint %d created: %s to %s",
                current.number,
                current.start_date,
                current.end_date,
            )
        elif is_monday and session == RunSession.PRE_MARKET:
            logger.info("Phase 0a: Monday sprint planning check...")

        # Daily standup.
        logger.info("Phase 0: Generating daily standup...")
        standup = generate_standup(current, session.value)
        logger.info("Standup generated: %s", standup.summary)

    except Exception:
        logger.exception("Ceremony phase failed (non-fatal)")


def _run_ceremonies_post(pipeline_run: SchedulerRun) -> None:
    """Phase 6-8: Run post-analysis ceremonies (Friday retro, sprint advance)."""
    from app.agile.ceremonies import generate_retro
    from app.agile.postmortem import detect_failures, save_postmortem
    from app.agile.store import advance_sprint, get_current_sprint, save_retro
    from app.finops.tracker import summarize_period

    today = datetime.now(tz=UTC).date()
    is_friday = today.weekday() == 4

    try:
        # Detect and save postmortems.
        logger.info("Phase 6: Checking for postmortem triggers...")
        failures = detect_failures(pipeline_run=pipeline_run)
        for item in failures:
            save_postmortem(item)
            logger.info("Postmortem created: %s", item.title)

        # Friday: sprint review + retrospective.
        if is_friday:
            current = get_current_sprint()
            if current:
                logger.info(
                    "Phase 7: Sprint %d review + retrospective...", current.number
                )

                # Calculate token spend for the sprint.
                token_summary = summarize_period(current.start_date, current.end_date)
                pipeline_rate = (
                    pipeline_run.succeeded / pipeline_run.total_modules * 100
                    if pipeline_run.total_modules > 0
                    else 0.0
                )

                retro = generate_retro(
                    current,
                    token_spend=token_summary.total_cost_usd,
                    pipeline_success_rate=pipeline_rate,
                )
                save_retro(retro)
                logger.info(
                    "Retrospective: velocity=%d, spend=$%.4f",
                    retro.velocity,
                    retro.token_spend_total,
                )

                # Phase 8: Auto-advance sprint.
                logger.info("Phase 8: Advancing sprint...")
                new_sprint = advance_sprint()
                logger.info("Advanced to Sprint %d", new_sprint.number)

    except Exception:
        logger.exception("Post-ceremony phase failed (non-fatal)")


def _record_token_usage(
    session: RunSession,
    stderr: str,
    duration: float,
) -> None:
    """Phase 5: Record token usage from Claude analysis."""
    from app.finops.tracker import parse_claude_output_tokens, record_usage

    try:
        input_tokens, output_tokens = parse_claude_output_tokens(stderr)
        if input_tokens > 0 or output_tokens > 0:
            today_str = datetime.now(tz=UTC).date().isoformat()
            record = record_usage(
                agent_name="exec-cio",
                session=session.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_seconds=duration,
                run_id=f"{today_str}_{session.value}",
            )
            logger.info(
                "Token usage recorded: %d input, %d output, $%.4f",
                record.input_tokens,
                record.output_tokens,
                record.cost_usd,
            )
        else:
            logger.info("No token data found in Claude stderr")
    except Exception:
        logger.exception("Token usage recording failed (non-fatal)")


def _record_pipeline_health(
    pipeline_run: SchedulerRun,
    session: RunSession,
) -> None:
    """Phase 5: Record pipeline run for DevOps trending."""
    from app.devops.health import record_pipeline_run

    try:
        record_pipeline_run(pipeline_run, session.value)
        logger.info("Pipeline health recorded for DevOps trending")
    except Exception:
        logger.exception("Pipeline health recording failed (non-fatal)")


def run_scheduled(session: RunSession) -> ScheduledRunResult:
    """Execute a complete scheduled run.

    Phases:
      0: Ceremonies (standup, Monday planning)
      1: Data pipeline
      2: Publish HTML report
      3: Claude analysis
      4: Telegram summary
      5: Record token usage + pipeline health
      6-8: Post-ceremonies (Friday retro, sprint advance)

    Each phase is independent — failure in one does not block the next.
    """
    config = SchedulerConfig.from_env()
    log_file = _setup_logging(config, session)

    started = datetime.now(tz=_ISRAEL_TZ).isoformat(timespec="seconds")
    logger.info("=" * 60)
    logger.info("SCHEDULED RUN: %s at %s", session.value, started)
    logger.info("Log file: %s", log_file)
    logger.info("=" * 60)

    # Phase 0: Pre-analysis ceremonies (standup, Monday planning)
    if session == RunSession.PRE_MARKET:
        _run_ceremonies_pre(session)

    # Phase 1: Data pipeline
    pipeline_run = _run_pipeline()

    # Phase 2: Publish HTML report
    publish_ok = _publish_report(pipeline_run)

    # Phase 3: Claude analysis — reads pipeline data and synthesizes.
    claude_ok, claude_output, claude_stderr, claude_duration = _run_claude_analysis(
        config,
        session,
        pipeline_run,
    )

    # Phase 4: Telegram summary
    telegram_ok = asyncio.run(
        _send_telegram_summary(
            pipeline_run,
            session,
            claude_output,
            claude_success=claude_ok,
        ),
    )

    # Phase 5: Record token usage and pipeline health
    _record_token_usage(session, claude_stderr, claude_duration)
    _record_pipeline_health(pipeline_run, session)

    # Phase 6-8: Post-analysis ceremonies (Friday retro + sprint advance)
    if session == RunSession.POST_MARKET:
        _run_ceremonies_post(pipeline_run)

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

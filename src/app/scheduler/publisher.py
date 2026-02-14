"""Publish HTML reports to docs/ for GitHub Pages."""

from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.scheduler.html_report import (
    build_about_html,
    build_financials_html,
    build_forecasts_html,
    build_html_report,
    build_index_html,
    build_research_html,
    build_roadmap_html,
    build_sprint_board_html,
    build_strategies_html,
    build_system_health_html,
    build_trade_log_html,
)
from app.scheduler.runner import SchedulerRun

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DOCS_DIR = _PROJECT_ROOT / "docs"
_REPORTS_DIR = _DOCS_DIR / "reports"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ensure_docs_dir() -> None:
    """Create docs/ and docs/reports/ if they don't exist."""
    _DOCS_DIR.mkdir(exist_ok=True)
    _REPORTS_DIR.mkdir(exist_ok=True)
    nojekyll = _DOCS_DIR / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.write_text("")


_SUB_PREFIXES = [
    "",
    "trade-log-",
    "forecasts-",
    "strategies-",
    "financials-",
    "sprint-board-",
    "roadmap-",
    "system-health-",
    "research-",
    "about-",
]

# Legacy prefixes that map to new ones (for old report discovery)
_LEGACY_PREFIX_MAP: dict[str, str] = {
    "trade-logs-": "trade-log-",
    "company-": "",  # company pages are deprecated
}


def _discover_report_dates() -> list[str]:
    """Scan docs/reports/ for existing YYYY-MM-DD.html files.

    Returns sorted list of date strings, newest first.
    """
    if not _REPORTS_DIR.exists():
        return []
    dates: list[str] = []
    for f in _REPORTS_DIR.glob("*.html"):
        stem = f.stem
        if _DATE_RE.match(stem):
            dates.append(stem)
    dates.sort(reverse=True)
    return dates


def _discover_sub_pages(dates: list[str]) -> dict[str, list[str]]:
    """For each date, discover which sub-page files exist.

    Returns ``{date: [prefix, ...]}`` where prefix is one of
    ``""``, ``"trade-log-"``, ``"forecasts-"``, etc.

    Also checks legacy prefixes (e.g. ``trade-logs-``) and maps them
    to current prefixes so old reports remain navigable.
    """
    result: dict[str, list[str]] = {}
    for d in dates:
        available: list[str] = []
        for pfx in _SUB_PREFIXES:
            if (_REPORTS_DIR / f"{pfx}{d}.html").exists():
                available.append(pfx)
        # Check legacy prefixes for backward compatibility
        for old_pfx, new_pfx in _LEGACY_PREFIX_MAP.items():
            if (
                new_pfx
                and new_pfx not in available
                and (_REPORTS_DIR / f"{old_pfx}{d}.html").exists()
            ):
                available.append(new_pfx)
        result[d] = available
    return result


def write_report(
    run: SchedulerRun,
    *,
    date: str = "",
) -> Path:
    """Generate HTML and write to docs/reports/YYYY-MM-DD.html.

    Also regenerates docs/index.html to include the new report.
    """
    report_date = date or datetime.now(tz=UTC).strftime("%Y-%m-%d")
    _ensure_docs_dir()

    # Discover existing dates early so the date picker is populated
    all_dates = _discover_report_dates()
    if report_date not in all_dates:
        all_dates.insert(0, report_date)
        all_dates.sort(reverse=True)

    report_html = build_html_report(
        run,
        date=report_date,
        report_dates=all_dates,
    )
    report_path = _REPORTS_DIR / f"{report_date}.html"
    report_path.write_text(report_html, encoding="utf-8")

    # Extract module outputs for data-driven pages
    outputs: dict[str, str] = {}
    for result in run.results:
        if result.success and result.output.strip():
            outputs[result.name] = result.output.strip()

    trade_log_html = build_trade_log_html(
        outputs,
        date=report_date,
        report_dates=all_dates,
    )
    if trade_log_html:
        trade_log_path = _REPORTS_DIR / f"trade-log-{report_date}.html"
        trade_log_path.write_text(trade_log_html, encoding="utf-8")

    forecasts_html = build_forecasts_html(
        outputs,
        date=report_date,
        report_dates=all_dates,
    )
    if forecasts_html:
        forecasts_path = _REPORTS_DIR / f"forecasts-{report_date}.html"
        forecasts_path.write_text(forecasts_html, encoding="utf-8")

    strategies_html = build_strategies_html(
        outputs,
        date=report_date,
        report_dates=all_dates,
    )
    if strategies_html:
        strategies_path = _REPORTS_DIR / f"strategies-{report_date}.html"
        strategies_path.write_text(strategies_html, encoding="utf-8")

    sprint_board_html = build_sprint_board_html(
        date=report_date,
        report_dates=all_dates,
    )
    if sprint_board_html:
        sprint_board_path = _REPORTS_DIR / f"sprint-board-{report_date}.html"
        sprint_board_path.write_text(sprint_board_html, encoding="utf-8")

    system_health_html = build_system_health_html(
        run,
        date=report_date,
        report_dates=all_dates,
    )
    if system_health_html:
        system_health_path = _REPORTS_DIR / f"system-health-{report_date}.html"
        system_health_path.write_text(system_health_html, encoding="utf-8")

    financials_html = build_financials_html(
        date=report_date,
        report_dates=all_dates,
    )
    if financials_html:
        financials_path = _REPORTS_DIR / f"financials-{report_date}.html"
        financials_path.write_text(financials_html, encoding="utf-8")

    about_html = build_about_html(
        date=report_date,
        report_dates=all_dates,
    )
    if about_html:
        about_path = _REPORTS_DIR / f"about-{report_date}.html"
        about_path.write_text(about_html, encoding="utf-8")

    roadmap_html = build_roadmap_html(
        date=report_date,
        report_dates=all_dates,
    )
    if roadmap_html:
        roadmap_path = _REPORTS_DIR / f"roadmap-{report_date}.html"
        roadmap_path.write_text(roadmap_html, encoding="utf-8")

    research_html_page = build_research_html(
        date=report_date,
        report_dates=all_dates,
    )
    if research_html_page:
        research_path = _REPORTS_DIR / f"research-{report_date}.html"
        research_path.write_text(research_html_page, encoding="utf-8")

    sub_pages = _discover_sub_pages(all_dates)
    index_html = build_index_html(all_dates, sub_pages=sub_pages)
    (_DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    return report_path


def _git(args: list[str], cwd: str) -> None:
    """Run a git command."""
    subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def git_publish(*, message: str = "") -> bool:
    """Stage docs/, commit, and push to origin."""
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    commit_msg = message or f"Update daily report {date_str}"

    cwd = str(_PROJECT_ROOT)
    try:
        _git(["git", "add", "docs/"], cwd)
        _git(["git", "commit", "-m", commit_msg], cwd)
        _git(["git", "push"], cwd)
    except subprocess.CalledProcessError:
        return False
    return True

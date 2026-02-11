"""Publish HTML reports to docs/ for GitHub Pages."""

from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.scheduler.html_report import build_html_report, build_index_html
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

    report_html = build_html_report(run, date=report_date)
    report_path = _REPORTS_DIR / f"{report_date}.html"
    report_path.write_text(report_html, encoding="utf-8")

    all_dates = _discover_report_dates()
    index_html = build_index_html(all_dates)
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

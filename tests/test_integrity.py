"""Project consistency guard.

Validates that cross-references between skills, agents, CLI modules,
documentation, and configuration stay in sync as the project evolves.

Run: uv run pytest tests/test_integrity.py -v
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from app.scheduler.runner import MODULE_COMMANDS
from app.telegram.dispatcher import _COMMAND_SKILLS, CommandDispatcher

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Expected confidence factor count — update when adding/removing factors.
# Source of truth: the number of assess_* functions in app.etf.confidence.
EXPECTED_FACTOR_COUNT = 14


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_section(text: str, heading: str) -> str:
    """Extract section content from *heading* to the next same-level heading."""
    level = len(heading) - len(heading.lstrip("#"))
    pattern = re.compile(rf"^{re.escape(heading)}\b.*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE)
    end_match = next_heading.search(text, start)
    end = end_match.start() if end_match else len(text)
    return text[start:end]


# ---------------------------------------------------------------------------
# Test 1: Dispatcher skill references → skill directories
# ---------------------------------------------------------------------------


def test_dispatcher_skills_exist() -> None:
    """Every skill referenced by _COMMAND_SKILLS must have a SKILL.md on disk."""
    skills_dir = PROJECT_ROOT / ".claude" / "skills"

    skill_names: set[str] = set()
    for prompt in _COMMAND_SKILLS.values():
        match = re.search(r"/(\S+)", prompt)
        if match:
            skill_names.add(match.group(1))

    missing = sorted(
        name
        for name in skill_names
        if not (skills_dir / name / "SKILL.md").exists()
    )

    assert not missing, (
        "Dispatcher references skills without SKILL.md:\n"
        + "\n".join(
            f"  - {n}  (expected .claude/skills/{n}/SKILL.md)" for n in missing
        )
    )


# ---------------------------------------------------------------------------
# Test 2: CLAUDE.md agents ↔ .claude/agents/ files
# ---------------------------------------------------------------------------


def test_agent_files_match_claude_md() -> None:
    """Every agent in CLAUDE.md must have a file, and every file must be listed."""
    agents_dir = PROJECT_ROOT / ".claude" / "agents"
    claude_md = _read_text(PROJECT_ROOT / "CLAUDE.md")

    section = _extract_section(claude_md, "### Agents")
    # Agent names follow the {dept}-{role} pattern.
    raw = set(re.findall(r"\b([a-z]+-[a-z][\w-]*)\b", section))
    noise = {"dept-role", "pre-market", "post-market"}
    documented = raw - noise

    on_disk = {p.stem for p in agents_dir.glob("*.md")}

    in_docs_not_disk = sorted(documented - on_disk)
    on_disk_not_docs = sorted(on_disk - documented)

    errors: list[str] = []
    if in_docs_not_disk:
        errors.append(
            "Agents in CLAUDE.md but missing .md files:\n"
            + "\n".join(
                f"  - {a}  (create .claude/agents/{a}.md)"
                for a in in_docs_not_disk
            )
        )
    if on_disk_not_docs:
        errors.append(
            "Agent files on disk not listed in CLAUDE.md:\n"
            + "\n".join(f"  - {a}.md" for a in on_disk_not_docs)
        )

    assert not errors, "\n\n".join(errors)


# ---------------------------------------------------------------------------
# Test 3: Scheduler MODULE_COMMANDS → src/app/<mod>/__main__.py
# ---------------------------------------------------------------------------


def test_scheduler_modules_exist() -> None:
    """Every module in MODULE_COMMANDS must have a __main__.py."""
    app_dir = PROJECT_ROOT / "src" / "app"

    modules = {name.split(".")[0] for name, _cmd in MODULE_COMMANDS}

    missing = sorted(
        mod
        for mod in modules
        if not (app_dir / mod / "__main__.py").exists()
    )

    assert not missing, (
        "Scheduler references modules without __main__.py:\n"
        + "\n".join(
            f"  - {m}  (expected src/app/{m}/__main__.py)" for m in missing
        )
    )


# ---------------------------------------------------------------------------
# Test 4: CLAUDE.md skill list ↔ .claude/skills/ directories
# ---------------------------------------------------------------------------


def test_claude_md_skills_match_disk() -> None:
    """Skills listed in CLAUDE.md must match actual skill directories."""
    skills_dir = PROJECT_ROOT / ".claude" / "skills"
    claude_md = _read_text(PROJECT_ROOT / "CLAUDE.md")

    section = _extract_section(claude_md, "### Skills")
    # Skills are comma-separated names after the em-dash on the `.claude/skills/` line.
    match = re.search(r"—\s*(.+)", section)
    if match:
        documented = {name.strip() for name in match.group(1).split(",")}
    else:
        documented = set()

    on_disk = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}

    in_docs_not_disk = sorted(documented - on_disk)
    on_disk_not_docs = sorted(on_disk - documented)

    errors: list[str] = []
    if in_docs_not_disk:
        errors.append(
            "Skills in CLAUDE.md but missing on disk:\n"
            + "\n".join(f"  - {s}" for s in in_docs_not_disk)
        )
    if on_disk_not_docs:
        errors.append(
            "Skill directories on disk not listed in CLAUDE.md:\n"
            + "\n".join(f"  - {s}" for s in on_disk_not_docs)
        )

    assert not errors, "\n\n".join(errors)


# ---------------------------------------------------------------------------
# Test 5: Dispatcher help text covers all commands
# ---------------------------------------------------------------------------


def test_dispatcher_help_covers_all_commands() -> None:
    """The help text in _handle_help must mention every _COMMAND_SKILLS key."""
    source = inspect.getsource(CommandDispatcher._handle_help)

    missing = sorted(cmd for cmd in _COMMAND_SKILLS if f"/{cmd}" not in source)

    assert not missing, (
        "Commands in _COMMAND_SKILLS not shown in /help:\n"
        + "\n".join(f"  - /{cmd}" for cmd in missing)
    )


# ---------------------------------------------------------------------------
# Test 6: Confidence factor count consistent across docs
# ---------------------------------------------------------------------------


def test_confidence_factor_count_consistent() -> None:
    """All documentation must reference the same factor count."""
    files_to_check: dict[str, Path] = {
        "CLAUDE.md": PROJECT_ROOT / "CLAUDE.md",
        "unified-report/SKILL.md": (
            PROJECT_ROOT / ".claude" / "skills" / "unified-report" / "SKILL.md"
        ),
        "team-report/SKILL.md": (
            PROJECT_ROOT / ".claude" / "skills" / "team-report" / "SKILL.md"
        ),
        "scheduled_run.py": (
            PROJECT_ROOT / "src" / "app" / "scheduler" / "scheduled_run.py"
        ),
        "exec-cio.md": PROJECT_ROOT / ".claude" / "agents" / "exec-cio.md",
    }

    # Matches patterns like "13 factors", "12 factors"
    pattern = re.compile(r"\b(\d+)\s+factors?\b")

    mismatches: list[str] = []
    for label, path in files_to_check.items():
        if not path.exists():
            mismatches.append(f"  - {label}: FILE NOT FOUND")
            continue
        content = _read_text(path)
        for match in pattern.finditer(content):
            count = int(match.group(1))
            if count != EXPECTED_FACTOR_COUNT:
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end].strip()
                mismatches.append(
                    f"  - {label}: says {count} factors"
                    f' ("{line[:80]}")'
                )

    assert not mismatches, (
        f"Inconsistent factor counts (expected {EXPECTED_FACTOR_COUNT}):\n"
        + "\n".join(mismatches)
    )


# ---------------------------------------------------------------------------
# Test 7: Factor count matches active assess_* functions in code
# ---------------------------------------------------------------------------


def test_confidence_factor_count_matches_code() -> None:
    """EXPECTED_FACTOR_COUNT must equal the number of assess_* functions."""
    import app.etf.confidence as confidence_mod

    assess_fns = sorted(
        name
        for name, obj in inspect.getmembers(confidence_mod, inspect.isfunction)
        if name.startswith("assess_")
    )

    assert len(assess_fns) == EXPECTED_FACTOR_COUNT, (
        f"Expected {EXPECTED_FACTOR_COUNT} assess_* functions, "
        f"found {len(assess_fns)}:\n"
        + "\n".join(f"  - {name}" for name in assess_fns)
        + "\n\nUpdate EXPECTED_FACTOR_COUNT if factors were added/removed."
    )

"""Research document CLI.

Usage:
    python -m app.research status                     Show research pipeline status
    python -m app.research list                       List all documents
    python -m app.research show <id>                  Show full document
    python -m app.research summary                    JSON summary for pipeline
    python -m app.research create --title T --type T --hypothesis H --priority P
    python -m app.research update <id> <section> --status S   (content via stdin)
    python -m app.research complete <id>              Mark document complete
    python -m app.research notes --text T --session S Save continuation notes
"""

from __future__ import annotations

import json
import sys

from app.research.models import (
    DocumentStatus,
    ResearchType,
    SectionStatus,
)
from app.research.store import (
    create_document,
    get_sprint_progress,
    list_documents,
    load_document,
    load_state,
    save_continuation_notes,
    set_document_status,
    update_section,
)


def _cmd_status() -> int:
    state = load_state()
    completed, target = get_sprint_progress(state.current_sprint)
    in_progress = [d for d in state.documents if d.status == DocumentStatus.IN_PROGRESS]
    ideas = [d for d in state.documents if d.status == DocumentStatus.IDEA]
    drafts = [d for d in state.documents if d.status == DocumentStatus.DRAFT]
    done = [d for d in state.documents if d.status == DocumentStatus.COMPLETE]

    print("=== Research Pipeline Status ===")  # noqa: T201
    print(f"Sprint {state.current_sprint}: {completed}/{target} documents complete")  # noqa: T201
    print(  # noqa: T201
        f"Total: {len(done)} complete, {len(drafts)} draft, "
        f"{len(in_progress)} in-progress, {len(ideas)} ideas",
    )
    print()  # noqa: T201

    if in_progress:
        print("IN-PROGRESS:")  # noqa: T201
        for d in in_progress:
            doc = load_document(d.id)
            if doc:
                filled = sum(1 for s in doc.sections if s.status != SectionStatus.EMPTY)
                print(f"  [{d.id}] {d.title} ({filled}/9 sections)")  # noqa: T201

    if ideas:
        print("IDEAS:")  # noqa: T201
        for d in ideas:
            print(f"  [{d.id}] {d.title}")  # noqa: T201

    if state.continuation_notes:
        print()  # noqa: T201
        print(f"CONTINUATION ({state.last_run_date} {state.last_run_session}):")  # noqa: T201
        print(f"  {state.continuation_notes}")  # noqa: T201

    return 0


def _cmd_list() -> int:
    docs = list_documents()
    if not docs:
        print("No research documents found.")  # noqa: T201
        return 0

    for doc in docs:
        filled = sum(1 for s in doc.sections if s.status != SectionStatus.EMPTY)
        complete = sum(1 for s in doc.sections if s.status == SectionStatus.COMPLETE)
        tags = ", ".join(doc.tags) if doc.tags else ""
        print(  # noqa: T201
            f"[{doc.id}] {doc.status.value:12s} {doc.research_type.value:16s} "
            f"S{doc.sprint_number} {complete}/{filled}/9 "
            f"{doc.priority:6s} {doc.title}"
            f"{f'  ({tags})' if tags else ''}",
        )
    return 0


def _cmd_show(doc_id: str) -> int:
    doc = load_document(doc_id)
    if doc is None:
        print(f"Document {doc_id} not found.", file=sys.stderr)  # noqa: T201
        return 1

    print(f"{'=' * 60}")  # noqa: T201
    print(f"  {doc.id}: {doc.title}")  # noqa: T201
    print(f"{'=' * 60}")  # noqa: T201
    print(  # noqa: T201
        f"Type: {doc.research_type.value} | Priority: {doc.priority}"
        f" | Status: {doc.status.value}",
    )
    print(  # noqa: T201
        f"Sprint: {doc.sprint_number} | Created: {doc.created_date}"
        f" | Updated: {doc.updated_date}",
    )
    if doc.tags:
        print(f"Tags: {', '.join(doc.tags)}")  # noqa: T201
    print(f"Hypothesis: {doc.hypothesis}")  # noqa: T201
    print()  # noqa: T201

    for section in doc.sections:
        markers = {"EMPTY": " ", "DRAFT": "~", "COMPLETE": "X"}
        status_marker = markers[section.status.value]
        print(f"[{status_marker}] {section.title}")  # noqa: T201
        if section.content:
            # Indent content for readability.
            for line in section.content.split("\n"):
                print(f"    {line}")  # noqa: T201
            print()  # noqa: T201

    return 0


def _cmd_summary() -> int:
    state = load_state()
    completed, target = get_sprint_progress(state.current_sprint)
    docs = list_documents()

    doc_entries: list[dict[str, object]] = []
    status_counts: dict[str, int] = {}
    for doc in docs:
        status_counts[doc.status.value] = (
            status_counts.get(doc.status.value, 0) + 1
        )
        filled = sum(
            1 for s in doc.sections
            if s.status != SectionStatus.EMPTY
        )
        complete_sections = sum(
            1 for s in doc.sections
            if s.status == SectionStatus.COMPLETE
        )
        doc_entries.append({
            "id": doc.id,
            "title": doc.title,
            "type": doc.research_type.value,
            "status": doc.status.value,
            "priority": doc.priority,
            "sprint": doc.sprint_number,
            "sections_filled": filled,
            "sections_complete": complete_sections,
            "sections_total": 9,
        })

    summary: dict[str, object] = {
        "sprint": state.current_sprint,
        "sprint_progress": f"{completed}/{target}",
        "total_documents": len(docs),
        "by_status": status_counts,
        "documents": doc_entries,
    }
    print(json.dumps(summary, indent=2))  # noqa: T201
    return 0


def _cmd_create(args: list[str]) -> int:
    title = _extract_flag(args, "--title")
    rtype = _extract_flag(args, "--type")
    hypothesis = _extract_flag(args, "--hypothesis")
    priority = _extract_flag(args, "--priority") or "MEDIUM"

    if not title or not rtype or not hypothesis:
        print("Required: --title, --type, --hypothesis", file=sys.stderr)  # noqa: T201
        return 1

    try:
        research_type = ResearchType(rtype.upper())
    except ValueError:
        valid = ", ".join(t.value for t in ResearchType)
        print(f"Invalid type '{rtype}'. Valid: {valid}", file=sys.stderr)  # noqa: T201
        return 1

    # Get current sprint from agile module.
    sprint = _current_sprint_number()

    tags_str = _extract_flag(args, "--tags")
    tags = [t.strip() for t in tags_str.split(",")] if tags_str else []

    doc = create_document(
        title=title,
        research_type=research_type,
        hypothesis=hypothesis,
        priority=priority,
        sprint=sprint,
        tags=tags,
    )
    print(f"Created {doc.id}: {doc.title}")  # noqa: T201
    return 0


def _cmd_update(args: list[str]) -> int:
    if len(args) < 2:
        print("Usage: update <id> <section_key> [--status STATUS]", file=sys.stderr)  # noqa: T201
        return 1

    doc_id = args[0]
    section_key = args[1]
    status_str = _extract_flag(args[2:], "--status") or "DRAFT"

    try:
        status = SectionStatus(status_str.upper())
    except ValueError:
        print(f"Invalid status '{status_str}'.", file=sys.stderr)  # noqa: T201
        return 1

    # Read content from stdin.
    if not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        content_flag = _extract_flag(args[2:], "--content")
        content = content_flag or ""

    if not content.strip():
        print("No content provided (pipe via stdin or --content).", file=sys.stderr)  # noqa: T201
        return 1

    try:
        doc = update_section(doc_id, section_key, content.strip(), status)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)  # noqa: T201
        return 1

    filled = sum(1 for s in doc.sections if s.status != SectionStatus.EMPTY)
    print(  # noqa: T201
        f"Updated {doc_id}/{section_key} -> {status.value}"
        f" ({filled}/9 sections filled)",
    )
    return 0


def _cmd_complete(doc_id: str) -> int:
    try:
        doc = set_document_status(doc_id, DocumentStatus.COMPLETE)
    except FileNotFoundError:
        print(f"Document {doc_id} not found.", file=sys.stderr)  # noqa: T201
        return 1
    print(f"Marked {doc.id} as COMPLETE: {doc.title}")  # noqa: T201
    return 0


def _cmd_notes(args: list[str]) -> int:
    text = _extract_flag(args, "--text")
    session = _extract_flag(args, "--session") or "unknown"

    if not text:
        # Try stdin.
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        if not text:
            print("Required: --text or pipe via stdin", file=sys.stderr)  # noqa: T201
            return 1

    save_continuation_notes(text, session)
    print(f"Continuation notes saved ({session}).")  # noqa: T201
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_flag(args: list[str], flag: str) -> str:
    """Extract a --flag value from args list."""
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args):
            return args[i + 1]
    return ""


def _current_sprint_number() -> int:
    """Get current sprint number from agile module."""
    try:
        from app.agile.store import get_current_sprint

        sprint = get_current_sprint()
        return sprint.number if sprint else 0
    except Exception:
        return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        return 1

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    match cmd:
        case "status":
            return _cmd_status()
        case "list":
            return _cmd_list()
        case "show":
            if not rest:
                print("Usage: show <id>", file=sys.stderr)  # noqa: T201
                return 1
            return _cmd_show(rest[0])
        case "summary":
            return _cmd_summary()
        case "create":
            return _cmd_create(rest)
        case "update":
            return _cmd_update(rest)
        case "complete":
            if not rest:
                print("Usage: complete <id>", file=sys.stderr)  # noqa: T201
                return 1
            return _cmd_complete(rest[0])
        case "notes":
            return _cmd_notes(rest)
        case _:
            print(f"Unknown command: {cmd}")  # noqa: T201
            print(__doc__)  # noqa: T201
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

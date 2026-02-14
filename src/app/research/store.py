"""Persistence layer for research documents and state."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.research.models import (
    SECTION_TEMPLATE,
    DocumentRef,
    DocumentStatus,
    ResearchDocument,
    ResearchSection,
    ResearchState,
    ResearchType,
    SectionStatus,
)

_RESEARCH_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "research"
)
_STATE_PATH = _RESEARCH_DIR / "state.json"
_DOCS_DIR = _RESEARCH_DIR / "documents"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def load_state(path: Path | None = None) -> ResearchState:
    """Load the global research state."""
    store = path or _STATE_PATH
    if not store.exists():
        return ResearchState()
    raw = json.loads(store.read_text(encoding="utf-8"))
    docs = []
    for d in raw.pop("documents", []):
        d["status"] = DocumentStatus(d["status"])
        docs.append(DocumentRef(**d))
    return ResearchState(documents=docs, **raw)


def save_state(state: ResearchState, path: Path | None = None) -> None:
    """Save the global research state."""
    store = path or _STATE_PATH
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(asdict(state), indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def _doc_path(doc_id: str, base: Path | None = None) -> Path:
    return (base or _DOCS_DIR) / f"{doc_id}.json"


def load_document(doc_id: str, base: Path | None = None) -> ResearchDocument | None:
    """Load a single research document by ID."""
    p = _doc_path(doc_id, base)
    if not p.exists():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    sections = []
    for s in raw.pop("sections", []):
        s["status"] = SectionStatus(s["status"])
        sections.append(ResearchSection(**s))
    raw["status"] = DocumentStatus(raw["status"])
    raw["research_type"] = ResearchType(raw["research_type"])
    return ResearchDocument(sections=sections, **raw)


def save_document(doc: ResearchDocument, base: Path | None = None) -> Path:
    """Save a research document."""
    p = _doc_path(doc.id, base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(asdict(doc), indent=2),
        encoding="utf-8",
    )
    return p


def list_documents(
    sprint: int | None = None,
    status: DocumentStatus | None = None,
    state_path: Path | None = None,
    docs_base: Path | None = None,
) -> list[ResearchDocument]:
    """List all documents, optionally filtered by sprint or status."""
    state = load_state(state_path)
    results: list[ResearchDocument] = []
    for ref in state.documents:
        if sprint is not None and ref.sprint_number != sprint:
            continue
        if status is not None and ref.status != status:
            continue
        doc = load_document(ref.id, docs_base)
        if doc is not None:
            results.append(doc)
    return results


def _next_id(state: ResearchState) -> str:
    """Generate the next document ID (RD-001, RD-002, ...)."""
    existing = [
        int(d.id.split("-")[1]) for d in state.documents
        if d.id.startswith("RD-")
    ]
    n = max(existing, default=0) + 1
    return f"RD-{n:03d}"


def create_document(
    title: str,
    research_type: ResearchType,
    hypothesis: str,
    priority: str,
    sprint: int,
    tags: list[str] | None = None,
    state_path: Path | None = None,
    docs_base: Path | None = None,
) -> ResearchDocument:
    """Create a new research document with empty sections."""
    state = load_state(state_path)
    doc_id = _next_id(state)
    now = datetime.now(tz=UTC).isoformat(timespec="seconds")

    sections = [
        ResearchSection(key=key, title=title_str)
        for key, title_str in SECTION_TEMPLATE
    ]

    doc = ResearchDocument(
        id=doc_id,
        title=title,
        research_type=research_type,
        hypothesis=hypothesis,
        priority=priority.upper(),
        status=DocumentStatus.IDEA,
        sections=sections,
        created_date=now,
        updated_date=now,
        sprint_number=sprint,
        tags=tags or [],
    )

    save_document(doc, docs_base)

    state.documents.append(
        DocumentRef(
            id=doc_id,
            title=title,
            status=DocumentStatus.IDEA,
            sprint_number=sprint,
        ),
    )
    save_state(state, state_path)

    return doc


def update_section(
    doc_id: str,
    section_key: str,
    content: str,
    status: SectionStatus = SectionStatus.DRAFT,
    docs_base: Path | None = None,
    state_path: Path | None = None,
) -> ResearchDocument:
    """Update one section of a document."""
    doc = load_document(doc_id, docs_base)
    if doc is None:
        msg = f"Document {doc_id} not found"
        raise FileNotFoundError(msg)

    found = False
    for section in doc.sections:
        if section.key == section_key:
            section.content = content
            section.status = status
            found = True
            break

    if not found:
        msg = f"Section '{section_key}' not found in {doc_id}"
        raise ValueError(msg)

    doc.updated_date = datetime.now(tz=UTC).isoformat(timespec="seconds")

    # Auto-transition document status.
    if doc.status == DocumentStatus.IDEA:
        doc.status = DocumentStatus.IN_PROGRESS

    all_done = all(s.status == SectionStatus.COMPLETE for s in doc.sections)
    all_have_content = all(s.status != SectionStatus.EMPTY for s in doc.sections)
    if all_done:
        doc.status = DocumentStatus.DRAFT
    elif all_have_content and doc.status == DocumentStatus.IDEA:
        doc.status = DocumentStatus.IN_PROGRESS

    save_document(doc, docs_base)

    # Sync state index.
    state = load_state(state_path)
    for ref in state.documents:
        if ref.id == doc_id:
            ref.status = doc.status
            break
    save_state(state, state_path)

    return doc


def set_document_status(
    doc_id: str,
    status: DocumentStatus,
    docs_base: Path | None = None,
    state_path: Path | None = None,
) -> ResearchDocument:
    """Manually set a document's status."""
    doc = load_document(doc_id, docs_base)
    if doc is None:
        msg = f"Document {doc_id} not found"
        raise FileNotFoundError(msg)

    doc.status = status
    doc.updated_date = datetime.now(tz=UTC).isoformat(timespec="seconds")
    save_document(doc, docs_base)

    state = load_state(state_path)
    for ref in state.documents:
        if ref.id == doc_id:
            ref.status = status
            break
    save_state(state, state_path)

    return doc


def get_sprint_progress(
    sprint_number: int,
    state_path: Path | None = None,
) -> tuple[int, int]:
    """Return (completed_count, target) for a sprint."""
    state = load_state(state_path)
    completed = sum(
        1
        for d in state.documents
        if d.sprint_number == sprint_number and d.status == DocumentStatus.COMPLETE
    )
    return completed, state.sprint_target


def save_continuation_notes(
    notes: str,
    session: str,
    state_path: Path | None = None,
) -> None:
    """Save continuation notes for the next run."""
    state = load_state(state_path)
    state.continuation_notes = notes
    state.last_run_date = datetime.now(tz=UTC).date().isoformat()
    state.last_run_session = session
    save_state(state, state_path)

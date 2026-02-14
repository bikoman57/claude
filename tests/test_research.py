"""Tests for the research document module."""

from __future__ import annotations

from pathlib import Path

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
    save_state,
    set_document_status,
    update_section,
)


def test_create_document(tmp_path: Path) -> None:
    """Create a research document and verify it has 9 empty sections."""
    state_path = tmp_path / "state.json"
    docs_base = tmp_path / "documents"

    doc = create_document(
        title="VIX Crush Strategy",
        research_type=ResearchType.NEW_STRATEGY,
        hypothesis="VIX crush entries outperform unconditional entries",
        priority="HIGH",
        sprint=4,
        tags=["VIX", "TQQQ"],
        state_path=state_path,
        docs_base=docs_base,
    )

    assert doc.id == "RD-001"
    assert doc.title == "VIX Crush Strategy"
    assert doc.research_type == ResearchType.NEW_STRATEGY
    assert doc.status == DocumentStatus.IDEA
    assert len(doc.sections) == 9
    assert all(s.status == SectionStatus.EMPTY for s in doc.sections)
    assert doc.sprint_number == 4
    assert doc.tags == ["VIX", "TQQQ"]


def test_auto_increment_id(tmp_path: Path) -> None:
    """IDs auto-increment: RD-001, RD-002, etc."""
    state_path = tmp_path / "state.json"
    docs_base = tmp_path / "documents"

    doc1 = create_document(
        title="Strategy A",
        research_type=ResearchType.NEW_STRATEGY,
        hypothesis="A",
        priority="LOW",
        sprint=1,
        state_path=state_path,
        docs_base=docs_base,
    )
    doc2 = create_document(
        title="Strategy B",
        research_type=ResearchType.NEW_ETF,
        hypothesis="B",
        priority="MEDIUM",
        sprint=1,
        state_path=state_path,
        docs_base=docs_base,
    )

    assert doc1.id == "RD-001"
    assert doc2.id == "RD-002"


def test_update_section(tmp_path: Path) -> None:
    """Update a section and verify status transitions."""
    state_path = tmp_path / "state.json"
    docs_base = tmp_path / "documents"

    create_document(
        title="Test Doc",
        research_type=ResearchType.MARKET_ANOMALY,
        hypothesis="Testing",
        priority="MEDIUM",
        sprint=4,
        state_path=state_path,
        docs_base=docs_base,
    )

    doc = update_section(
        "RD-001",
        "executive_summary",
        "This study examines...",
        SectionStatus.DRAFT,
        docs_base=docs_base,
        state_path=state_path,
    )

    assert doc.status == DocumentStatus.IN_PROGRESS
    assert doc.sections[0].content == "This study examines..."
    assert doc.sections[0].status == SectionStatus.DRAFT


def test_complete_all_sections(tmp_path: Path) -> None:
    """Completing all sections transitions doc to DRAFT."""
    state_path = tmp_path / "state.json"
    docs_base = tmp_path / "documents"

    create_document(
        title="Full Doc",
        research_type=ResearchType.NEW_STRATEGY,
        hypothesis="Test",
        priority="HIGH",
        sprint=4,
        state_path=state_path,
        docs_base=docs_base,
    )

    section_keys = [
        "executive_summary", "background", "data_description",
        "statistical_methods", "results", "interpretation",
        "limitations", "conclusion", "appendix",
    ]

    doc = None
    for key in section_keys:
        doc = update_section(
            "RD-001", key, f"Content for {key}",
            SectionStatus.COMPLETE,
            docs_base=docs_base,
            state_path=state_path,
        )

    assert doc is not None
    assert doc.status == DocumentStatus.DRAFT


def test_set_document_status(tmp_path: Path) -> None:
    """Manually set document status to COMPLETE."""
    state_path = tmp_path / "state.json"
    docs_base = tmp_path / "documents"

    create_document(
        title="To Complete",
        research_type=ResearchType.NEW_STRATEGY,
        hypothesis="Test",
        priority="HIGH",
        sprint=4,
        state_path=state_path,
        docs_base=docs_base,
    )

    doc = set_document_status(
        "RD-001", DocumentStatus.COMPLETE,
        docs_base=docs_base,
        state_path=state_path,
    )

    assert doc.status == DocumentStatus.COMPLETE

    # Verify state index is synced.
    state = load_state(state_path)
    assert state.documents[0].status == DocumentStatus.COMPLETE


def test_sprint_progress(tmp_path: Path) -> None:
    """Count completed documents for a sprint."""
    state_path = tmp_path / "state.json"
    docs_base = tmp_path / "documents"

    create_document(
        title="A", research_type=ResearchType.NEW_STRATEGY,
        hypothesis="A", priority="HIGH", sprint=4,
        state_path=state_path, docs_base=docs_base,
    )
    create_document(
        title="B", research_type=ResearchType.NEW_ETF,
        hypothesis="B", priority="MEDIUM", sprint=4,
        state_path=state_path, docs_base=docs_base,
    )
    create_document(
        title="C", research_type=ResearchType.NEW_STRATEGY,
        hypothesis="C", priority="LOW", sprint=5,
        state_path=state_path, docs_base=docs_base,
    )

    # Complete first doc.
    set_document_status(
        "RD-001", DocumentStatus.COMPLETE,
        docs_base=docs_base, state_path=state_path,
    )

    completed, target = get_sprint_progress(4, state_path)
    assert completed == 1
    assert target == 5  # default target

    # Sprint 5 should have 0.
    completed5, _ = get_sprint_progress(5, state_path)
    assert completed5 == 0


def test_list_documents_filter(tmp_path: Path) -> None:
    """List documents with filters."""
    state_path = tmp_path / "state.json"
    docs_base = tmp_path / "documents"

    create_document(
        title="A", research_type=ResearchType.NEW_STRATEGY,
        hypothesis="A", priority="HIGH", sprint=4,
        state_path=state_path, docs_base=docs_base,
    )
    create_document(
        title="B", research_type=ResearchType.NEW_ETF,
        hypothesis="B", priority="MEDIUM", sprint=5,
        state_path=state_path, docs_base=docs_base,
    )

    all_docs = list_documents(state_path=state_path, docs_base=docs_base)
    assert len(all_docs) == 2

    sprint4_docs = list_documents(sprint=4, state_path=state_path, docs_base=docs_base)
    assert len(sprint4_docs) == 1
    assert sprint4_docs[0].title == "A"


def test_continuation_notes(tmp_path: Path) -> None:
    """Save and load continuation notes."""
    state_path = tmp_path / "state.json"
    save_state(load_state(state_path), state_path)

    save_continuation_notes(
        "Continue with data_description section for RD-001",
        "pre-market",
        state_path,
    )

    state = load_state(state_path)
    assert "RD-001" in state.continuation_notes
    assert state.last_run_session == "pre-market"


def test_load_document_not_found(tmp_path: Path) -> None:
    """Loading a non-existent document returns None."""
    result = load_document("RD-999", tmp_path)
    assert result is None


def test_state_round_trip(tmp_path: Path) -> None:
    """State saves and loads correctly."""
    from app.research.models import ResearchState

    state_path = tmp_path / "state.json"
    state = ResearchState(sprint_target=3, current_sprint=4)
    save_state(state, state_path)

    loaded = load_state(state_path)
    assert loaded.sprint_target == 3
    assert loaded.current_sprint == 4
    assert loaded.documents == []

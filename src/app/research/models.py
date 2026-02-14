"""Research document data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SectionStatus(StrEnum):
    """Status of a research document section."""

    EMPTY = "EMPTY"
    DRAFT = "DRAFT"
    COMPLETE = "COMPLETE"


class DocumentStatus(StrEnum):
    """Lifecycle status of a research document."""

    IDEA = "IDEA"
    IN_PROGRESS = "IN_PROGRESS"
    DRAFT = "DRAFT"
    COMPLETE = "COMPLETE"
    ARCHIVED = "ARCHIVED"


class ResearchType(StrEnum):
    """Type of research being conducted."""

    NEW_STRATEGY = "NEW_STRATEGY"
    NEW_ETF = "NEW_ETF"
    MARKET_ANOMALY = "MARKET_ANOMALY"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"


SECTION_TEMPLATE: list[tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("background", "Background & Objective"),
    ("data_description", "Data Description"),
    ("statistical_methods", "Statistical Methods"),
    ("results", "Results"),
    ("interpretation", "Interpretation & Discussion"),
    ("limitations", "Limitations"),
    ("conclusion", "Conclusion & Recommendations"),
    ("appendix", "Appendix"),
]


@dataclass
class ResearchSection:
    """One section of a research document."""

    key: str
    title: str
    content: str = ""
    status: SectionStatus = SectionStatus.EMPTY


@dataclass
class ResearchDocument:
    """A full research document with 9 sections."""

    id: str
    title: str
    research_type: ResearchType
    hypothesis: str
    priority: str
    status: DocumentStatus
    sections: list[ResearchSection] = field(default_factory=list)
    created_date: str = ""
    updated_date: str = ""
    sprint_number: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class DocumentRef:
    """Lightweight reference to a document in the state index."""

    id: str
    title: str
    status: DocumentStatus
    sprint_number: int


@dataclass
class ResearchState:
    """Global research pipeline state persisted between runs."""

    documents: list[DocumentRef] = field(default_factory=list)
    sprint_target: int = 5
    current_sprint: int = 0
    last_run_date: str = ""
    last_run_session: str = ""
    continuation_notes: str = ""

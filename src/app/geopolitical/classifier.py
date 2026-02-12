from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class GeopoliticalImpact(StrEnum):
    """Impact level of a geopolitical event."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class GeopoliticalCategory(StrEnum):
    """Category of a geopolitical event."""

    TRADE_WAR = "TRADE_WAR"
    MILITARY = "MILITARY"
    SANCTIONS = "SANCTIONS"
    ELECTIONS = "ELECTIONS"
    TERRITORIAL = "TERRITORIAL"
    POLICY = "POLICY"


CATEGORY_SECTOR_MAP: dict[str, list[str]] = {
    "TRADE_WAR": ["tech", "semiconductors"],
    "ECON_TARIFF": ["tech", "semiconductors"],
    "MILITARY": ["energy", "defense"],
    "SANCTIONS": ["energy", "finance"],
    "ELECTION": ["general"],
    "ELECTIONS": ["general"],
    "TERRITORY": ["semiconductors", "tech"],
    "TERRITORIAL": ["semiconductors", "tech"],
    "POLICY": ["finance", "general"],
}

_CATEGORY_MAPPING: dict[str, GeopoliticalCategory] = {
    "TRADE_WAR": GeopoliticalCategory.TRADE_WAR,
    "ECON_TARIFF": GeopoliticalCategory.TRADE_WAR,
    "MILITARY": GeopoliticalCategory.MILITARY,
    "SANCTIONS": GeopoliticalCategory.SANCTIONS,
    "ELECTION": GeopoliticalCategory.ELECTIONS,
    "TERRITORY": GeopoliticalCategory.TERRITORIAL,
}


@dataclass(frozen=True, slots=True)
class ClassifiedEvent:
    """A geopolitical event with market impact classification."""

    title: str
    url: str
    category: GeopoliticalCategory
    impact: GeopoliticalImpact
    affected_sectors: tuple[str, ...]
    tone: float
    date: str


@dataclass(frozen=True, slots=True)
class GeopoliticalSummary:
    """Aggregated geopolitical risk summary."""

    risk_level: str
    high_impact_count: int
    total_events: int
    events_by_category: dict[str, int]
    affected_sectors: dict[str, int]
    top_events: tuple[ClassifiedEvent, ...]
    as_of: str


def classify_impact(tone: float, volume: int = 0) -> GeopoliticalImpact:
    """Classify event impact based on tone and article volume.

    Tone alone drives classification since GDELT DOC API does not
    provide per-article volume metrics.
    """
    if tone < -5 or volume > 500:
        return GeopoliticalImpact.HIGH
    if tone < -2 or volume > 50:
        return GeopoliticalImpact.MEDIUM
    return GeopoliticalImpact.LOW


def classify_event(
    title: str,
    url: str,
    theme: str,
    tone: float,
    volume: int,
    date: str,
) -> ClassifiedEvent:
    """Classify a geopolitical event."""
    category = _CATEGORY_MAPPING.get(theme, GeopoliticalCategory.POLICY)
    impact = classify_impact(tone, volume)
    sectors = CATEGORY_SECTOR_MAP.get(theme, ["general"])

    return ClassifiedEvent(
        title=title,
        url=url,
        category=category,
        impact=impact,
        affected_sectors=tuple(sectors),
        tone=tone,
        date=date,
    )


def build_geopolitical_summary(
    events: list[ClassifiedEvent],
    top_n: int = 5,
) -> GeopoliticalSummary:
    """Build an aggregated geopolitical risk summary."""
    high_count = sum(1 for e in events if e.impact == GeopoliticalImpact.HIGH)

    if high_count >= 3:
        risk = "HIGH"
    elif high_count >= 1:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    cat_counts: dict[str, int] = {}
    sector_counts: dict[str, int] = {}
    for e in events:
        cat_counts[e.category] = cat_counts.get(e.category, 0) + 1
        for s in e.affected_sectors:
            sector_counts[s] = sector_counts.get(s, 0) + 1

    # Sort by impact (HIGH first) then by tone (most negative first)
    sorted_events = sorted(
        events,
        key=lambda e: (
            0
            if e.impact == GeopoliticalImpact.HIGH
            else 1
            if e.impact == GeopoliticalImpact.MEDIUM
            else 2,
            e.tone,
        ),
    )

    return GeopoliticalSummary(
        risk_level=risk,
        high_impact_count=high_count,
        total_events=len(events),
        events_by_category=cat_counts,
        affected_sectors=sector_counts,
        top_events=tuple(sorted_events[:top_n]),
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )

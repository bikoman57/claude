from __future__ import annotations

import contextlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.social.sentiment import classify_fed_tone, classify_sentiment

_ATOM_NAMESPACE = "{http://www.w3.org/2005/Atom}"


@dataclass(frozen=True, slots=True)
class OfficialStatement:
    """A statement from a key government/institutional figure."""

    speaker: str
    source: str
    title: str
    date: str
    sentiment: str


@dataclass(frozen=True, slots=True)
class OfficialsSummary:
    """Summary of official statements."""

    statements: tuple[OfficialStatement, ...]
    fed_tone: str
    policy_direction: str
    total_statements: int
    as_of: str


OFFICIAL_FEEDS: list[tuple[str, str]] = [
    ("Fed Speeches", "https://www.federalreserve.gov/feeds/speeches.xml"),
    ("SEC Press", "https://www.sec.gov/news/pressreleases.rss"),
]


def fetch_fed_speeches() -> list[OfficialStatement]:
    """Fetch Federal Reserve speeches from RSS/Atom feed."""
    url = OFFICIAL_FEEDS[0][1]
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)  # noqa: S314
    statements: list[OfficialStatement] = []

    # Try RSS format first
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        if not title:
            continue
        date = item.findtext("pubDate", "").strip()
        link = item.findtext("link", "").strip()
        desc = item.findtext("description", "").strip()
        tone = classify_fed_tone(f"{title} {desc}")
        statements.append(
            OfficialStatement(
                speaker="Federal Reserve",
                source=link,
                title=title,
                date=date,
                sentiment=tone,
            ),
        )

    # Try Atom format if no RSS items found
    if not statements:
        for entry in root.iter(f"{_ATOM_NAMESPACE}entry"):
            title = entry.findtext(f"{_ATOM_NAMESPACE}title", "").strip()
            if not title:
                continue
            date = entry.findtext(f"{_ATOM_NAMESPACE}updated", "").strip()
            link_el = entry.find(f"{_ATOM_NAMESPACE}link")
            link = link_el.get("href", "") if link_el is not None else ""
            summary = entry.findtext(
                f"{_ATOM_NAMESPACE}summary", "",
            ).strip()
            tone = classify_fed_tone(f"{title} {summary}")
            statements.append(
                OfficialStatement(
                    speaker="Federal Reserve",
                    source=link,
                    title=title,
                    date=date,
                    sentiment=tone,
                ),
            )

    return statements


def fetch_sec_press_releases() -> list[OfficialStatement]:
    """Fetch SEC press releases from RSS feed."""
    url = OFFICIAL_FEEDS[1][1]
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, follow_redirects=True)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)  # noqa: S314
    statements: list[OfficialStatement] = []
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        if not title:
            continue
        statements.append(
            OfficialStatement(
                speaker="SEC",
                source=item.findtext("link", "").strip(),
                title=title,
                date=item.findtext("pubDate", "").strip(),
                sentiment=classify_sentiment(title),
            ),
        )
    return statements


def fetch_all_official_statements() -> list[OfficialStatement]:
    """Fetch all official statements, skipping errors."""
    all_statements: list[OfficialStatement] = []
    with contextlib.suppress(Exception):
        all_statements.extend(fetch_fed_speeches())
    with contextlib.suppress(Exception):
        all_statements.extend(fetch_sec_press_releases())
    return all_statements


def build_officials_summary(
    statements: list[OfficialStatement],
) -> OfficialsSummary:
    """Build summary of official statements."""
    fed_statements = [s for s in statements if s.speaker == "Federal Reserve"]

    hawkish = sum(1 for s in fed_statements if s.sentiment == "HAWKISH")
    dovish = sum(1 for s in fed_statements if s.sentiment == "DOVISH")

    if hawkish > dovish:
        fed_tone = "HAWKISH"
        direction = "CONTRACTIONARY"
    elif dovish > hawkish:
        fed_tone = "DOVISH"
        direction = "EXPANSIONARY"
    else:
        fed_tone = "NEUTRAL"
        direction = "NEUTRAL"

    return OfficialsSummary(
        statements=tuple(statements),
        fed_tone=fed_tone,
        policy_direction=direction,
        total_statements=len(statements),
        as_of=datetime.now(tz=UTC).isoformat(timespec="seconds"),
    )

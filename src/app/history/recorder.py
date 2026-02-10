from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

_HISTORY_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "history"
)


@dataclass(frozen=True, slots=True)
class FactorSnapshot:
    """A snapshot of one analysis factor."""

    name: str
    value: str
    assessment: str  # FAVORABLE / UNFAVORABLE / NEUTRAL


@dataclass
class AnalysisSnapshot:
    """A complete analysis snapshot at a point in time."""

    timestamp: str
    signals: list[dict[str, object]]
    factors: list[FactorSnapshot]
    summary: str


def create_snapshot(
    signals: list[dict[str, object]],
    factors: list[FactorSnapshot],
    summary: str,
) -> AnalysisSnapshot:
    """Create a new snapshot with current timestamp."""
    return AnalysisSnapshot(
        timestamp=datetime.now(tz=UTC).isoformat(timespec="seconds"),
        signals=signals,
        factors=factors,
        summary=summary,
    )


def save_snapshot(
    snapshot: AnalysisSnapshot,
    directory: Path | None = None,
) -> Path:
    """Save a snapshot to a timestamped JSON file."""
    dir_path = directory or _HISTORY_DIR
    dir_path.mkdir(parents=True, exist_ok=True)
    dt = datetime.fromisoformat(snapshot.timestamp)
    filename = dt.strftime("%Y-%m-%d_%H-%M") + ".json"
    file_path = dir_path / filename
    file_path.write_text(
        json.dumps(asdict(snapshot), indent=2),
        encoding="utf-8",
    )
    return file_path


def load_snapshot(path: Path) -> AnalysisSnapshot:
    """Load a snapshot from a JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    factors = [
        FactorSnapshot(
            name=f["name"],
            value=f["value"],
            assessment=f["assessment"],
        )
        for f in raw["factors"]
    ]
    return AnalysisSnapshot(
        timestamp=raw["timestamp"],
        signals=raw["signals"],
        factors=factors,
        summary=raw["summary"],
    )


def list_snapshots(directory: Path | None = None) -> list[Path]:
    """List all snapshot files, newest first."""
    dir_path = directory or _HISTORY_DIR
    if not dir_path.exists():
        return []
    return sorted(dir_path.glob("*.json"), reverse=True)

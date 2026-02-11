from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.etf.signals import Signal, SignalState

_DEFAULT_STORE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "signals.json"
)


def load_signals(path: Path | None = None) -> list[Signal]:
    """Load signals from the JSON store file."""
    store_path = path or _DEFAULT_STORE_PATH
    if not store_path.exists():
        return []
    raw: list[dict[str, object]] = json.loads(store_path.read_text(encoding="utf-8"))
    return [
        Signal(**{**s, "state": SignalState(str(s["state"]))})  # type: ignore[arg-type]
        for s in raw
    ]


def save_signals(signals: list[Signal], path: Path | None = None) -> None:
    """Save signals to the JSON store file."""
    store_path = path or _DEFAULT_STORE_PATH
    store_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(s) for s in signals]
    store_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_active_signals(path: Path | None = None) -> list[Signal]:
    """Load only signals in ACTIVE state."""
    return [s for s in load_signals(path) if s.state == SignalState.ACTIVE]


def get_actionable_signals(path: Path | None = None) -> list[Signal]:
    """Load signals in SIGNAL or TARGET state (require user action)."""
    return [
        s
        for s in load_signals(path)
        if s.state in {SignalState.SIGNAL, SignalState.TARGET}
    ]

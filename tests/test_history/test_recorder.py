from __future__ import annotations

from app.history.recorder import (
    AnalysisSnapshot,
    FactorSnapshot,
    create_snapshot,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)


def test_create_snapshot():
    snap = create_snapshot(
        signals=[{"ticker": "TQQQ", "state": "SIGNAL"}],
        factors=[FactorSnapshot("vix", "15.2", "FAVORABLE")],
        summary="1 signal detected",
    )
    assert snap.timestamp
    assert len(snap.signals) == 1
    assert len(snap.factors) == 1
    assert snap.summary == "1 signal detected"


def test_save_load_roundtrip(tmp_path):
    snap = create_snapshot(
        signals=[{"ticker": "TQQQ", "state": "SIGNAL"}],
        factors=[
            FactorSnapshot("vix", "15.2", "FAVORABLE"),
            FactorSnapshot("fed", "PAUSING", "NEUTRAL"),
        ],
        summary="Test snapshot",
    )
    path = save_snapshot(snap, directory=tmp_path)
    assert path.exists()

    loaded = load_snapshot(path)
    assert loaded.timestamp == snap.timestamp
    assert loaded.summary == snap.summary
    assert len(loaded.factors) == 2
    assert loaded.factors[0].name == "vix"
    assert loaded.factors[0].assessment == "FAVORABLE"
    assert loaded.signals == snap.signals


def test_list_snapshots_ordering(tmp_path):
    snap1 = AnalysisSnapshot(
        timestamp="2025-01-15T10:00:00+00:00",
        signals=[],
        factors=[],
        summary="First",
    )
    snap2 = AnalysisSnapshot(
        timestamp="2025-01-16T10:00:00+00:00",
        signals=[],
        factors=[],
        summary="Second",
    )
    save_snapshot(snap1, directory=tmp_path)
    save_snapshot(snap2, directory=tmp_path)

    snapshots = list_snapshots(directory=tmp_path)
    assert len(snapshots) == 2
    # Newest first
    assert "2025-01-16" in snapshots[0].name
    assert "2025-01-15" in snapshots[1].name


def test_list_snapshots_empty(tmp_path):
    snapshots = list_snapshots(directory=tmp_path)
    assert snapshots == []

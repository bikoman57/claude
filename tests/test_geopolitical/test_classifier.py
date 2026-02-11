from __future__ import annotations

from app.geopolitical.classifier import (
    GeopoliticalCategory,
    GeopoliticalImpact,
    build_geopolitical_summary,
    classify_event,
    classify_impact,
)


def test_classify_impact_high_tone_volume():
    assert classify_impact(-6.0, 150) == GeopoliticalImpact.HIGH


def test_classify_impact_high_volume_only():
    assert classify_impact(0.0, 600) == GeopoliticalImpact.HIGH


def test_classify_impact_medium_tone():
    assert classify_impact(-3.0, 10) == GeopoliticalImpact.MEDIUM


def test_classify_impact_medium_volume():
    assert classify_impact(0.0, 60) == GeopoliticalImpact.MEDIUM


def test_classify_impact_low():
    assert classify_impact(1.0, 10) == GeopoliticalImpact.LOW


def test_classify_event_trade_war():
    ce = classify_event("Trade war", "url", "TRADE_WAR", -6.0, 200, "2026")
    assert ce.category == GeopoliticalCategory.TRADE_WAR
    assert ce.impact == GeopoliticalImpact.HIGH
    assert "tech" in ce.affected_sectors


def test_classify_event_military():
    ce = classify_event("Conflict", "url", "MILITARY", -1.0, 20, "2026")
    assert ce.category == GeopoliticalCategory.MILITARY
    assert "energy" in ce.affected_sectors


def test_classify_event_unknown_theme():
    ce = classify_event("Unknown", "url", "UNKNOWN", 0.0, 5, "2026")
    assert ce.category == GeopoliticalCategory.POLICY


def test_summary_high_risk():
    events = [
        classify_event("A", "", "TRADE_WAR", -6.0, 200, ""),
        classify_event("B", "", "MILITARY", -7.0, 300, ""),
        classify_event("C", "", "SANCTIONS", -8.0, 600, ""),
    ]
    summary = build_geopolitical_summary(events)
    assert summary.risk_level == "HIGH"
    assert summary.high_impact_count == 3


def test_summary_low_risk():
    events = [
        classify_event("A", "", "ELECTION", 1.0, 10, ""),
        classify_event("B", "", "POLICY", 0.5, 5, ""),
    ]
    summary = build_geopolitical_summary(events)
    assert summary.risk_level == "LOW"
    assert summary.high_impact_count == 0


def test_summary_medium_risk():
    events = [
        classify_event("A", "", "TRADE_WAR", -6.0, 200, ""),
        classify_event("B", "", "ELECTION", 1.0, 10, ""),
    ]
    summary = build_geopolitical_summary(events)
    assert summary.risk_level == "MEDIUM"


def test_summary_sector_counts():
    events = [
        classify_event("A", "", "TRADE_WAR", -3.0, 60, ""),
        classify_event("B", "", "TRADE_WAR", -2.5, 55, ""),
    ]
    summary = build_geopolitical_summary(events)
    assert summary.affected_sectors.get("tech", 0) == 2


def test_summary_top_n():
    events = [
        classify_event(f"Event {i}", "", "MILITARY", -1.0, 10, "")
        for i in range(10)
    ]
    summary = build_geopolitical_summary(events, top_n=3)
    assert len(summary.top_events) == 3

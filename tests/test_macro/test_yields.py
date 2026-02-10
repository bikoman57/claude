from __future__ import annotations

from app.macro.yields import classify_curve


def test_classify_curve_normal():
    assert classify_curve(1.5) == "NORMAL"


def test_classify_curve_inverted():
    assert classify_curve(-0.5) == "INVERTED"


def test_classify_curve_flat():
    assert classify_curve(0.1) == "FLAT"
    assert classify_curve(-0.1) == "FLAT"


def test_classify_curve_unknown():
    assert classify_curve(None) == "UNKNOWN"


def test_classify_curve_boundary():
    assert classify_curve(0.25) == "FLAT"
    # Just above threshold
    assert classify_curve(0.26) == "NORMAL"
    assert classify_curve(-0.26) == "INVERTED"

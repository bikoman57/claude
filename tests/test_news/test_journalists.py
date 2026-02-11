from __future__ import annotations

import pytest

from app.news.journalists import (
    load_journalist_ratings,
    update_journalist_rating,
)


def test_load_empty(tmp_path):
    path = tmp_path / "ratings.json"
    ratings = load_journalist_ratings(path)
    assert ratings == []


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "ratings.json"
    updated = update_journalist_rating("Jane", "Reuters", True, path)
    assert updated.name == "Jane"
    assert updated.accuracy == pytest.approx(1.0)

    loaded = load_journalist_ratings(path)
    assert len(loaded) == 1
    assert loaded[0].name == "Jane"


def test_update_correct(tmp_path):
    path = tmp_path / "ratings.json"
    update_journalist_rating("Jane", "Reuters", True, path)
    update_journalist_rating("Jane", "Reuters", True, path)
    updated = update_journalist_rating("Jane", "Reuters", False, path)
    assert updated.articles_tracked == 3
    assert updated.correct_predictions == 2
    assert updated.accuracy == pytest.approx(2 / 3)


def test_update_incorrect(tmp_path):
    path = tmp_path / "ratings.json"
    updated = update_journalist_rating("Bob", "BBC", False, path)
    assert updated.accuracy == pytest.approx(0.0)
    assert updated.articles_tracked == 1


def test_multiple_journalists(tmp_path):
    path = tmp_path / "ratings.json"
    update_journalist_rating("Jane", "Reuters", True, path)
    update_journalist_rating("Bob", "BBC", False, path)
    ratings = load_journalist_ratings(path)
    assert len(ratings) == 2
    names = {r.name for r in ratings}
    assert names == {"Jane", "Bob"}

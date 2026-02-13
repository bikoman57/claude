"""Tests for FinOps budget management."""

from __future__ import annotations

from pathlib import Path

from app.finops.budget import (
    DEFAULT_BUDGETS,
    init_budgets,
    load_budgets,
    save_budgets,
    suggest_reallocation,
)
from app.finops.models import BudgetConfig, DepartmentBudget, DepartmentROI


class TestBudgetPersistence:
    def test_init_creates_default(self, tmp_path: Path) -> None:
        budget_path = tmp_path / "budgets.json"
        config = init_budgets(budget_path)
        assert len(config.budgets) == len(DEFAULT_BUDGETS)
        assert config.total_weekly_usd == 100.0

    def test_load_after_save(self, tmp_path: Path) -> None:
        budget_path = tmp_path / "budgets.json"
        config = BudgetConfig(
            budgets=[DepartmentBudget("test", 10.0, 40.0, "normal")],
            total_weekly_usd=10.0,
            total_monthly_usd=40.0,
            last_updated="2026-02-12",
        )
        save_budgets(config, budget_path)
        loaded = load_budgets(budget_path)
        assert len(loaded.budgets) == 1
        assert loaded.budgets[0].department == "test"

    def test_load_missing_returns_default(self, tmp_path: Path) -> None:
        budget_path = tmp_path / "nonexistent.json"
        config = load_budgets(budget_path)
        assert len(config.budgets) == len(DEFAULT_BUDGETS)


class TestSuggestReallocation:
    def test_empty_roi(self) -> None:
        suggestions = suggest_reallocation([])
        assert len(suggestions) == 1
        assert "No ROI data" in suggestions[0]

    def test_suggests_shift_to_high_roi(self) -> None:
        roi_data = [
            DepartmentROI("research", "week-1", 10.0, 50.0, 60.0, 95.0, 5.0),
            DepartmentROI("operations", "week-1", 5.0, -10.0, 0.0, 80.0, -2.0),
        ]
        suggestions = suggest_reallocation(roi_data)
        assert any("research" in s.lower() for s in suggestions)

    def test_all_acceptable(self) -> None:
        roi_data = [
            DepartmentROI("research", "week-1", 10.0, 20.0, 60.0, 95.0, 2.0),
            DepartmentROI("trading", "week-1", 15.0, 30.0, 70.0, 95.0, 2.0),
        ]
        suggestions = suggest_reallocation(roi_data)
        # Should still suggest shifting from lower to higher ROI.
        assert len(suggestions) >= 1

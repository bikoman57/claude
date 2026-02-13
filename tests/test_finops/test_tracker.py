"""Tests for FinOps token tracking."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.finops.models import ModelTier
from app.finops.tracker import (
    compute_cost,
    load_usage,
    parse_claude_output_tokens,
    record_usage,
    summarize_day,
)


class TestParseClaudeOutputTokens:
    def test_parse_standard_format(self) -> None:
        stderr = "Input tokens: 15000, Output tokens: 3000"
        input_t, output_t = parse_claude_output_tokens(stderr)
        assert input_t == 15000
        assert output_t == 3000

    def test_parse_with_commas(self) -> None:
        stderr = "Input tokens: 1,500,000, Output tokens: 250,000"
        input_t, output_t = parse_claude_output_tokens(stderr)
        assert input_t == 1500000
        assert output_t == 250000

    def test_parse_no_match(self) -> None:
        stderr = "Some other output"
        input_t, output_t = parse_claude_output_tokens(stderr)
        assert input_t == 0
        assert output_t == 0

    def test_parse_mixed_case(self) -> None:
        stderr = "input tokens: 500\noutput tokens: 200"
        input_t, output_t = parse_claude_output_tokens(stderr)
        assert input_t == 500
        assert output_t == 200

    def test_parse_embedded_in_log(self) -> None:
        stderr = (
            "[INFO] Starting analysis...\n"
            "Input tokens: 42000, Output tokens: 8500\n"
            "[INFO] Done."
        )
        input_t, output_t = parse_claude_output_tokens(stderr)
        assert input_t == 42000
        assert output_t == 8500


class TestComputeCost:
    def test_opus_cost(self) -> None:
        cost = compute_cost(ModelTier.OPUS, 1_000_000, 100_000)
        # 1M * 15 / 1M + 100K * 75 / 1M = 15 + 7.5 = 22.5
        assert cost == pytest.approx(22.5)

    def test_sonnet_cost(self) -> None:
        cost = compute_cost(ModelTier.SONNET, 1_000_000, 100_000)
        # 1M * 3 / 1M + 100K * 15 / 1M = 3 + 1.5 = 4.5
        assert cost == pytest.approx(4.5)

    def test_haiku_cost(self) -> None:
        cost = compute_cost(ModelTier.HAIKU, 1_000_000, 100_000)
        # 1M * 0.25 / 1M + 100K * 1.25 / 1M = 0.25 + 0.125 = 0.375
        assert cost == pytest.approx(0.375)

    def test_zero_tokens(self) -> None:
        cost = compute_cost(ModelTier.OPUS, 0, 0)
        assert cost == 0.0


class TestRecordUsage:
    def test_record_and_load(self, tmp_path: Path) -> None:
        usage_path = tmp_path / "token_usage.json"

        record = record_usage(
            agent_name="exec-cio",
            session="pre-market",
            input_tokens=10000,
            output_tokens=2000,
            duration_seconds=120.0,
            run_id="2026-02-12_pre-market",
            path=usage_path,
        )

        assert record.agent_name == "exec-cio"
        assert record.department == "executive"
        assert record.model_tier == "opus"
        assert record.input_tokens == 10000
        assert record.output_tokens == 2000
        assert record.cost_usd > 0

        records = load_usage(path=usage_path)
        assert len(records) == 1
        assert records[0].agent_name == "exec-cio"

    def test_default_model_is_sonnet(self, tmp_path: Path) -> None:
        usage_path = tmp_path / "token_usage.json"

        record = record_usage(
            agent_name="research-macro",
            session="post-market",
            input_tokens=5000,
            output_tokens=1000,
            duration_seconds=60.0,
            path=usage_path,
        )

        assert record.model_tier == "sonnet"

    def test_multiple_records(self, tmp_path: Path) -> None:
        usage_path = tmp_path / "token_usage.json"

        record_usage("exec-cio", "pre-market", 100, 50, 10.0, path=usage_path)
        record_usage("research-macro", "pre-market", 200, 100, 20.0, path=usage_path)

        records = load_usage(path=usage_path)
        assert len(records) == 2


class TestSummarizeDay:
    def test_summarize_empty(self, tmp_path: Path) -> None:
        usage_path = tmp_path / "token_usage.json"
        summary = summarize_day("2026-02-12", path=usage_path)
        assert summary.record_count == 0
        assert summary.total_cost_usd == 0.0

    def test_summarize_with_records(self, tmp_path: Path) -> None:
        usage_path = tmp_path / "token_usage.json"
        record_usage("exec-cio", "pre-market", 10000, 2000, 60.0, path=usage_path)
        record_usage("research-macro", "pre-market", 5000, 1000, 30.0, path=usage_path)

        # Get today's date since records use datetime.now.
        from datetime import UTC, datetime

        today = datetime.now(tz=UTC).date().isoformat()
        summary = summarize_day(today, path=usage_path)
        assert summary.record_count == 2
        assert summary.total_cost_usd > 0
        assert "executive" in summary.by_department
        assert "research" in summary.by_department

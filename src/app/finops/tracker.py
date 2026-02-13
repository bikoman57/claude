"""Token usage capture, cost computation, and persistence."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.finops.models import (
    MODEL_COSTS,
    DailyTokenSummary,
    ModelTier,
    TokenUsageRecord,
)

_FINOPS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "finops"
_USAGE_PATH = _FINOPS_DIR / "token_usage.json"

# Agent -> model tier mapping.
AGENT_MODEL_MAP: dict[str, ModelTier] = {
    "exec-cio": ModelTier.OPUS,
    "exec-coo": ModelTier.HAIKU,
    "research-strategy-researcher": ModelTier.OPUS,
    "research-quant": ModelTier.OPUS,
    "ops-code-reviewer": ModelTier.HAIKU,
    "ops-security-reviewer": ModelTier.HAIKU,
    "ops-token-optimizer": ModelTier.HAIKU,
    "ops-devops": ModelTier.HAIKU,
}

# Agent -> department mapping.
AGENT_DEPARTMENT_MAP: dict[str, str] = {
    "exec-cio": "executive",
    "exec-coo": "executive",
    "trading-drawdown-monitor": "trading",
    "trading-market-analyst": "trading",
    "trading-swing-screener": "trading",
    "research-macro": "research",
    "research-sec": "research",
    "research-statistics": "research",
    "research-strategy-analyst": "research",
    "research-strategy-researcher": "research",
    "research-quant": "research",
    "intel-chief": "intelligence",
    "intel-news": "intelligence",
    "intel-geopolitical": "intelligence",
    "intel-social": "intelligence",
    "intel-congress": "intelligence",
    "risk-manager": "risk",
    "risk-portfolio": "risk",
    "ops-code-reviewer": "operations",
    "ops-design-reviewer": "operations",
    "ops-security-reviewer": "operations",
    "ops-token-optimizer": "operations",
    "ops-devops": "operations",
}


def parse_claude_output_tokens(stderr: str) -> tuple[int, int]:
    """Parse token counts from Claude CLI verbose output.

    Returns (input_tokens, output_tokens).
    """
    input_match = re.search(r"[Ii]nput\s+tokens?:\s*(\d[\d,]*)", stderr)
    output_match = re.search(r"[Oo]utput\s+tokens?:\s*(\d[\d,]*)", stderr)
    input_t = int(input_match.group(1).replace(",", "")) if input_match else 0
    output_t = int(output_match.group(1).replace(",", "")) if output_match else 0
    return input_t, output_t


def compute_cost(
    model: ModelTier,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Compute USD cost from token counts and model tier."""
    input_rate, output_rate = MODEL_COSTS[model]
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def record_usage(
    agent_name: str,
    session: str,
    input_tokens: int,
    output_tokens: int,
    duration_seconds: float,
    run_id: str = "",
    *,
    path: Path | None = None,
) -> TokenUsageRecord:
    """Record one agent invocation's token usage."""
    model = AGENT_MODEL_MAP.get(agent_name, ModelTier.SONNET)
    dept = AGENT_DEPARTMENT_MAP.get(agent_name, "unknown")
    cost = compute_cost(model, input_tokens, output_tokens)
    record = TokenUsageRecord(
        timestamp=datetime.now(tz=UTC).isoformat(timespec="seconds"),
        session=session,
        agent_name=agent_name,
        department=dept,
        model_tier=model.value,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost, 6),
        duration_seconds=duration_seconds,
        run_id=run_id,
    )
    _append_record(record, path=path)
    return record


def _append_record(
    record: TokenUsageRecord,
    *,
    path: Path | None = None,
) -> None:
    """Append a token usage record to the JSON store."""
    store = path or _USAGE_PATH
    store.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    if store.exists():
        records = json.loads(store.read_text(encoding="utf-8"))
    records.append(asdict(record))
    store.write_text(json.dumps(records, indent=2), encoding="utf-8")


def load_usage(
    since: str | None = None,
    *,
    path: Path | None = None,
) -> list[TokenUsageRecord]:
    """Load token usage records, optionally filtered by date."""
    store = path or _USAGE_PATH
    if not store.exists():
        return []
    raw: list[dict[str, object]] = json.loads(
        store.read_text(encoding="utf-8"),
    )
    records = [TokenUsageRecord(**r) for r in raw]  # type: ignore[arg-type]
    if since:
        records = [r for r in records if r.timestamp >= since]
    return records


def summarize_day(
    date_str: str,
    *,
    path: Path | None = None,
) -> DailyTokenSummary:
    """Aggregate token usage for a single day."""
    records = load_usage(path=path)
    day_records = [r for r in records if r.timestamp.startswith(date_str)]
    return _aggregate(date_str, day_records)


def summarize_period(
    start: str,
    end: str,
    *,
    path: Path | None = None,
) -> DailyTokenSummary:
    """Aggregate token usage for a date range."""
    records = load_usage(path=path)
    period_records = [r for r in records if start <= r.timestamp <= end + "Z"]
    return _aggregate(f"{start}_to_{end}", period_records)


def _aggregate(label: str, records: list[TokenUsageRecord]) -> DailyTokenSummary:
    """Build a summary from a list of records."""
    summary = DailyTokenSummary(date=label)
    for r in records:
        summary.total_input_tokens += r.input_tokens
        summary.total_output_tokens += r.output_tokens
        summary.total_cost_usd += r.cost_usd
        summary.by_department[r.department] = (
            summary.by_department.get(r.department, 0.0) + r.cost_usd
        )
        summary.by_agent[r.agent_name] = (
            summary.by_agent.get(r.agent_name, 0.0) + r.cost_usd
        )
        summary.by_model[r.model_tier] = (
            summary.by_model.get(r.model_tier, 0.0) + r.cost_usd
        )
        summary.record_count += 1
    summary.total_cost_usd = round(summary.total_cost_usd, 6)
    return summary

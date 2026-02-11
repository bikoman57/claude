"""Daily report generation and Telegram delivery."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.scheduler.runner import SchedulerRun
from app.telegram.client import TelegramClient
from app.telegram.config import TelegramConfig
from app.telegram.formatting import bold, escape_markdown


def _section(title: str, content: str) -> str:
    """Format a report section."""
    return f"{bold(title)}\n{escape_markdown(content)}"


def _parse_output(
    output: str,
) -> dict[str, object] | list[object] | None:
    """Try to parse JSON from module output."""
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return None


def build_report_text(run: SchedulerRun) -> str:
    """Build the daily report from scheduler run results."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    lines: list[str] = []

    header = f"DAILY SWING TRADING REPORT - {now}"
    lines.append(bold(header))
    lines.append("")

    # Module status summary
    status = f"Modules: {run.succeeded}/{run.total_modules} OK | Failed: {run.failed}"
    lines.append(escape_markdown(status))
    lines.append("")

    # Collect outputs by module
    outputs: dict[str, str] = {}
    for result in run.results:
        if result.success and result.output.strip():
            outputs[result.name] = result.output.strip()

    # Market overview from macro dashboard + rates
    if "macro.dashboard" in outputs:
        data = _parse_output(outputs["macro.dashboard"])
        if isinstance(data, dict):
            vix = data.get("vix_regime", "N/A")
            fed = "N/A"
            rates = _parse_output(outputs.get("macro.rates", ""))
            if isinstance(rates, dict):
                fed = str(rates.get("trajectory", "N/A"))
            section = f"VIX: {vix} | Fed: {fed}"
            lines.append(_section("MARKET OVERVIEW", section))
            lines.append("")

    # Geopolitical
    if "geopolitical.summary" in outputs:
        data = _parse_output(outputs["geopolitical.summary"])
        if isinstance(data, dict):
            risk = data.get("risk_level", "N/A")
            events = data.get("total_events", 0)
            section = f"Risk: {risk} | Events: {events}"
            lines.append(
                _section("GEOPOLITICAL", section),
            )
            lines.append("")

    # Social sentiment
    if "social.summary" in outputs:
        data = _parse_output(outputs["social.summary"])
        if isinstance(data, dict):
            officials = data.get("officials", {})
            tone = "N/A"
            if isinstance(officials, dict):
                tone = officials.get("fed_tone", "N/A")
            section = f"Officials tone: {tone}"
            lines.append(
                _section("SOCIAL & OFFICIALS", section),
            )
            lines.append("")

    # News
    if "news.summary" in outputs:
        data = _parse_output(outputs["news.summary"])
        if isinstance(data, dict):
            sentiment = data.get("sentiment", "N/A")
            count = data.get("total_articles", 0)
            section = f"Sentiment: {sentiment} ({count} articles)"
            lines.append(
                _section("NEWS", section),
            )
            lines.append("")

    # Statistics
    if "statistics.dashboard" in outputs:
        data = _parse_output(outputs["statistics.dashboard"])
        if isinstance(data, dict):
            risk = data.get("risk_indicators", {})
            assessment = "N/A"
            if isinstance(risk, dict):
                assessment = risk.get("risk_assessment", "N/A")
            section = f"Risk assessment: {assessment}"
            lines.append(
                _section("MARKET STATISTICS", section),
            )
            lines.append("")

    # ETF signals
    if "etf.signals" in outputs:
        data = _parse_output(outputs["etf.signals"])
        if isinstance(data, list) and data:
            signal_lines = []
            for sig in data[:5]:
                if isinstance(sig, dict):
                    ticker = sig.get("leveraged_ticker", "?")
                    state = sig.get("state", "?")
                    dd = sig.get(
                        "underlying_drawdown_pct",
                        0,
                    )
                    dd_str = f"{dd:.1%}" if isinstance(dd, float) else str(dd)
                    signal_lines.append(
                        f"{ticker}: {state} (dd: {dd_str})",
                    )
            if signal_lines:
                section = "\n".join(signal_lines)
                lines.append(
                    _section("ENTRY SIGNALS", section),
                )
                lines.append("")

    # Strategy proposals
    if "strategy.proposals" in outputs:
        data = _parse_output(outputs["strategy.proposals"])
        if isinstance(data, list) and data:
            prop_lines = []
            for p in data[:3]:
                if isinstance(p, dict):
                    ticker = p.get("leveraged_ticker", "?")
                    reason = p.get("improvement_reason", "")
                    prop_lines.append(f"{ticker}: {reason}")
            if prop_lines:
                section = "\n".join(prop_lines)
                lines.append(
                    _section("STRATEGY INSIGHTS", section),
                )
                lines.append("")

    # Failed modules warning
    failed = [r.name for r in run.results if not r.success]
    if failed:
        section = ", ".join(failed)
        lines.append(
            _section("WARNINGS", f"Failed: {section}"),
        )
        lines.append("")

    lines.append(
        escape_markdown("This is not financial advice."),
    )

    return "\n".join(lines)


async def send_daily_report(run: SchedulerRun) -> bool:
    """Build and send the daily report via Telegram."""
    try:
        config = TelegramConfig.from_env()
    except ValueError:
        return False

    text = build_report_text(run)
    try:
        async with TelegramClient(config) as client:
            await client.send_message(text)
        return True
    except Exception:
        return False

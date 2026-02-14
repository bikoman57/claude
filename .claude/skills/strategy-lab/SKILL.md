---
name: strategy-lab
description: Strategy analysis — proposals, backtests, forecasts, and research pipeline status. Use when user says "strategy lab", "backtest", "optimize strategy", "strategy proposals", "forecast", "verify forecasts", "strategy analysis".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Strategy Lab

Analyze strategies, backtests, forecasts, and research pipeline. $ARGUMENTS

## Instructions

### Step 1: Current Strategy State

```bash
uv run python -m app.strategy proposals
uv run python -m app.strategy forecast
uv run python -m app.strategy verify
```

### Step 2: Ticker Deep-Dive (if ticker provided in $ARGUMENTS)

If the user specifies a ticker (e.g., `/strategy-lab TQQQ`):

```bash
uv run python -m app.strategy compare <ticker>
uv run python -m app.strategy optimize <ticker>
uv run python -m app.strategy history <ticker>
```

If no ticker is specified, skip this step.

### Step 3: Research Pipeline Status

```bash
uv run python -m app.research status
uv run python -m app.research list
```

### Step 4: Strategy Analyst Assessment

Use the `research-strategy-analyst` agent to:
> "Assess the current strategy proposals against market conditions. Which parameter changes have the strongest statistical backing? Are there any forecasts that should be updated? Prioritize actionable recommendations."

Provide the agent with all CLI outputs from Steps 1-3.

### Step 5: Compile Report

```
=== STRATEGY LAB -- [DATE] ===

CURRENT PROPOSALS: [N] parameter changes suggested
| ETF   | Strategy         | Change           | Sharpe Δ | Win Rate |
|-------|------------------|------------------|----------|----------|
| ...   | ...              | ...              | ...      | ...      |

FORECAST ACCURACY:
Verified [N] past forecasts: [accuracy]%

ACTIVE FORECASTS:
| ETF   | Direction | Confidence | Basis              |
|-------|-----------|------------|--------------------|
| ...   | ...       | ...        | ...                |

[If ticker-specific deep-dive]:
DEEP DIVE: [TICKER]
Best strategy: [type] at [threshold]% / [target]%
Sharpe: [val] | Win rate: [%] | Max DD: [%] | Trades: [N]
All strategies compared:
| Strategy           | Sharpe | Win% | Trades | Avg P/L |
|--------------------|--------|------|--------|---------|
| ...                | ...    | ...  | ...    | ...     |

RESEARCH PIPELINE:
Sprint [N]: [completed]/[target] documents
In-progress: [document titles]
Ideas: [document titles]

ANALYST ASSESSMENT:
[research-strategy-analyst synthesis and top recommendations]

This is not financial advice.
```

No Telegram notification (this is an analysis tool, not an alert).

## Troubleshooting

**No backtests saved**: Run `uv run python -m app.strategy backtest-all` first to populate data.

**No research documents**: Run `/research start` to kick off the research pipeline.

**Unknown ticker**: Check `uv run python -m app.etf universe` for supported tickers.

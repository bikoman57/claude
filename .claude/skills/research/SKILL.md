---
name: research
description: Check research pipeline status or start/continue a research session. Use when user says "research status", "start research", "continue research", "research pipeline", "what's being researched", "run research".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Research

Research pipeline management and strategy discovery. $ARGUMENTS

## Instructions

### Step 1: Check Research State

```bash
uv run python -m app.research status
uv run python -m app.research list
```

### Step 2: Determine Mode

Based on $ARGUMENTS:

**Status mode** (default — user says "research", "research status", "research pipeline"):
- Display the pipeline overview from Step 1 and stop. Do NOT invoke any agent.

**Show mode** (user provides a document ID, e.g., "research RD-003"):
```bash
uv run python -m app.research show <id>
```
- Display the full document and stop.

**Active mode** (user says "start research", "continue research", "run research"):
- Continue to Step 3.

### Step 3: Gather Market Context (active mode only)

```bash
uv run python -m app.etf scan
uv run python -m app.quant regime
```

### Step 4: Invoke Strategy Researcher (active mode only)

Use the `research-strategy-researcher` agent:
> "Here is the current research pipeline status and market context. Decide whether to continue an in-progress document or start a new one based on priority and market conditions. Follow the 9-section research document format. Save continuation notes for the next session."

Provide the agent with:
- Research status and list from Step 1
- ETF scan and regime data from Step 3

### Step 5: Output Format

**Status mode:**
```
=== RESEARCH PIPELINE -- [DATE] ===

Sprint [N]: [completed]/[target] documents

IN-PROGRESS:
[ID] [title] ([filled]/9 sections) -- Priority: [P1/P2/P3]

IDEAS:
[ID] [title] -- Priority: [P1/P2/P3]

COMPLETED (this sprint):
[ID] [title]

CONTINUATION NOTES:
[last saved notes with context for next session]
```

**Active mode:**
The research-strategy-researcher agent will produce its own output, including the research document progress and continuation notes.

No Telegram notification.

## Troubleshooting

**No research documents**: The pipeline starts empty. Use "start research" to create the first document.

**Agent runs too long**: The research-strategy-researcher has built-in termination criteria (15 tool calls max). It will save continuation notes automatically.

---
name: ops-health
description: Operations health dashboard — system grade, pipeline status, token spending, sprint progress, and scheduler status. Use when user says "ops health", "system health", "pipeline status", "token spending", "budget", "sprint status", "is everything working".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: workflow-automation
---

# Operations Health

Operational health dashboard across DevOps, FinOps, and Agile. $ARGUMENTS

## Instructions

### Step 1: Gather DevOps Data

```bash
uv run python -m app.devops health
uv run python -m app.devops pipeline
uv run python -m app.devops trends
```

### Step 2: Gather FinOps Data

```bash
uv run python -m app.finops dashboard
uv run python -m app.finops budget
uv run python -m app.finops roi
```

### Step 3: Gather Agile & Scheduler Data

```bash
uv run python -m app.agile sprint
uv run python -m app.agile tasks
uv run python -m app.scheduler status
```

### Step 4: Compile Dashboard

No agent needed — synthesize the data directly:

```
=== OPERATIONS HEALTH -- [DATE] ===

SYSTEM: [HEALTHY/DEGRADED/DOWN] -- Grade: [A-F] ([score]%)

PIPELINE (7-day):
| Module         | Success Rate | Trend     | Last Failure |
|----------------|-------------|-----------|--------------|
| ...            | ...         | [up/down] | ...          |
[highlight modules below 80% success rate]

TOKEN SPENDING (this week):
Total: $[spent] / $[budget] ([%] used)
| Department   | Spent  | Budget | %    | Alert     |
|--------------|--------|--------|------|-----------|
| Executive    | $[val] | $[val] | [%]  | [OK/WARN] |
| Trading      | $[val] | $[val] | [%]  | [OK/WARN] |
| Research     | $[val] | $[val] | [%]  | [OK/WARN] |
| Intelligence | $[val] | $[val] | [%]  | [OK/WARN] |
| Risk         | $[val] | $[val] | [%]  | [OK/WARN] |
| Operations   | $[val] | $[val] | [%]  | [OK/WARN] |

TOP ROI:
| Department   | Cost   | Value Generated | ROI   |
|--------------|--------|-----------------|-------|
| ...          | ...    | ...             | ...   |

SPRINT STATUS:
Sprint [N]: [done]/[total] tasks ([%] complete)
Goals: [sprint goals]
Days remaining: [N]

LAST PIPELINE RUN:
[timestamp]: [OK]/[total] modules succeeded
Duration: [seconds]s

ISSUES:
- [any failing modules, budget overruns, stale data, blocked tasks]
```

### Step 5: Telegram Alert (conditional)

If system grade is D or F (DEGRADED/DOWN):
```bash
uv run python -m app.telegram notify --title "Ops Alert" "System grade: [grade] -- [top issue]"
```

If system is healthy, do NOT send a notification.

## Troubleshooting

**No pipeline data**: First run hasn't happened yet. Run `uv run python -m app.scheduler test-run` to populate.

**No finops data**: Run `uv run python -m app.finops init` to initialize budgets.

**No sprint**: Run `uv run python -m app.agile init` to initialize Sprint 1.

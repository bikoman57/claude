---
name: risk-check
description: Combined risk and portfolio check — exposure limits, position sizing, active P/L, and veto assessment. Use when user says "risk check", "portfolio status", "position sizing", "am I over-exposed", "exposure check", "risk dashboard", "how's my portfolio".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Risk Check

Risk and portfolio assessment with veto analysis. $ARGUMENTS

## Instructions

### Step 1: Gather Risk and Portfolio Data

```bash
uv run python -m app.risk dashboard
uv run python -m app.risk check
uv run python -m app.portfolio dashboard
uv run python -m app.portfolio allocations
uv run python -m app.portfolio sizing
uv run python -m app.etf active
```

### Step 2: Check Pending Signals

```bash
uv run python -m app.etf scan
```

### Step 3: Risk Manager Assessment

Use the `risk-manager` agent to:
> "Assess portfolio risk status. Check if any pending SIGNAL-state ETFs would breach risk limits. Flag active positions approaching stop-loss or profit target. Evaluate sector concentration. Recommend position sizing for any new entries."

Provide the agent with all CLI outputs from Steps 1-2.

### Step 4: Compile Report

```
=== RISK & PORTFOLIO CHECK -- [DATE] ===

PORTFOLIO:
Total: $[val] | Invested: $[val] ([%]) | Cash: $[val] ([%])
Realized P/L: $[val] | Unrealized P/L: $[val]

SECTOR ALLOCATION:
| Sector       | Value  | %    | Status          |
|--------------|--------|------|-----------------|
| Tech         | $[val] | [%]  | [OK/HIGH/LIMIT] |
| ...          | ...    | ...  | ...             |

ACTIVE POSITIONS:
| ETF  | Entry  | Current | P/L   | Target | Stop | Days |
|------|--------|---------|-------|--------|------|------|
| ...  | ...    | ...     | ...   | ...    | ...  | ...  |

RISK STATUS: [WITHIN LIMITS / WARNING / VETO ACTIVE]
Positions: [N]/[max] | Sector max: [%]/[limit]% | Cash: [%]/[min]%

PENDING SIGNALS:
[TICKER] -- [APPROVED / VETOED: reason]
Suggested size: $[val] ([%] of portfolio)

POSITION SIZING:
Fixed-Fraction (2% risk): $[val] per position
Half-Kelly: $[val] per position

RISK ASSESSMENT:
[risk-manager agent synthesis and recommendations]

This is not financial advice.
```

### Step 5: Telegram Alert (conditional)

If WARNING or VETO conditions detected:
```bash
uv run python -m app.telegram notify --title "Risk Alert" "[status]: [key issue]"
```

If all within limits, do NOT send a notification.

## Troubleshooting

**No active positions**: Portfolio sections will show $0 invested. This is normal for new setups.

**No pending signals**: Pending signals section will say "No ETFs in SIGNAL state."

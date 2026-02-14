---
name: intel-briefing
description: Generate a cross-referenced intelligence briefing from all sources (news, geopolitical, social, congress, prediction markets). Use when user says "intel briefing", "intelligence report", "what's the news", "sentiment check", "what's happening in the market".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.0.0
  category: financial-analysis
---

# Intelligence Briefing

Generate a unified intelligence briefing from all sources. $ARGUMENTS

## Instructions

### Step 1: Gather All Intelligence Data

Run all 5 intelligence CLIs (these are independent — run in parallel if possible):

```bash
uv run python -m app.news summary
uv run python -m app.geopolitical summary
uv run python -m app.social summary
uv run python -m app.congress summary
uv run python -m app.polymarket summary
```

### Step 2: Cross-Reference with Intel Chief

Use the `intel-chief` agent to cross-reference all 5 sources:
> "Cross-reference these intelligence sources. Identify contradictions between sources, flag contrarian setups (bearish sentiment + congress buying = opportunity), and produce a sector-by-sector sentiment breakdown mapped to our ETF universe."

Provide the agent with all 5 CLI outputs.

### Step 3: Compile Briefing

```
=== INTELLIGENCE BRIEFING -- [DATE] ===

OVERALL: [BULLISH/BEARISH/NEUTRAL] ([HIGH/MEDIUM/LOW] confidence)

NEWS: [sentiment] ([N] articles)
- [top headline with sector relevance]

GEOPOLITICAL: [risk level]
- [top event with sector impact]

SOCIAL: Reddit [sentiment] | Officials: Fed [HAWKISH/DOVISH/NEUTRAL]
- [key takeaway]

CONGRESS: [sentiment] ($[net] net buying, last 30 days)
- [top sector flow and notable member trades]

PREDICTION MARKETS: [overall signal]
- [top market + probability with relevance]

CROSS-REFERENCE:
- [contradictions between sources]
- [confirmations across sources]
- [contrarian setups identified]

SECTOR SENTIMENT MATRIX:
| Sector       | News | Geo  | Social | Congress | Polymarket | Net       |
|--------------|------|------|--------|----------|------------|-----------|
| Tech         | ...  | ...  | ...    | ...      | ...        | [signal]  |
| Semis        | ...  | ...  | ...    | ...      | ...        | [signal]  |
| Finance      | ...  | ...  | ...    | ...      | ...        | [signal]  |
| Energy       | ...  | ...  | ...    | ...      | ...        | [signal]  |
| Biotech      | ...  | ...  | ...    | ...      | ...        | [signal]  |
| Broad/SmCap  | ...  | ...  | ...    | ...      | ...        | [signal]  |

KEY FINDING: [single most impactful intelligence item]

This is not financial advice.
```

### Step 4: Telegram Alert (conditional)

If any sector has strong contrarian setup or actionable signal:
```bash
uv run python -m app.telegram notify --title "Intel Briefing" "<key finding + actionable sectors>"
```

If no actionable signals, do NOT send a notification (avoid noise).

## Troubleshooting

**Missing Reddit credentials**: Social module will skip Reddit data. Note partial data.

**No congressional trades**: Congress module returns empty if no recent disclosures.

**Polymarket unavailable**: Note missing prediction market data and continue with 4 sources.

**Weekend/holiday**: Some sources may have stale data. Note in the briefing.

---
name: self-improve
description: Audit and improve this project's Claude Code configuration against latest best practices. Use when user says "self-improve", "audit config", "update best practices", or "optimize Claude setup".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 2.0.0
  category: workflow-automation
---

# Self-Improvement Cycle

Run a self-improvement audit for this project. $ARGUMENTS

## Instructions

### Step 1: Fetch Latest Best Practices

Fetch both sources using WebFetch:
1. `https://code.claude.com/docs/en/best-practices` — Claude Code environment best practices
2. `https://code.claude.com/docs/en/skills` — Skills documentation

Extract actionable recommendations. Focus on what changed since the last improvement cycle (check `.claude/improvements.log` for the last run date).

### Step 2: Audit CLAUDE.md

Read `CLAUDE.md` and evaluate against these criteria:

- **Conciseness**: For each line, ask "Would removing this cause Claude to make mistakes?" If not, cut it.
- **No defaults**: Remove anything Claude already does correctly without being told (standard language conventions, obvious patterns).
- **Actionable rules**: Every line must be specific and actionable, not vague ("write clean code" is bad, "use `pathlib.Path` instead of `os.path`" is good).
- **Not too long**: If Claude keeps ignoring rules, the file is probably too bloated and rules are getting lost.
- **Emphasis for critical rules**: Use "IMPORTANT" or "CRITICAL" for rules that must never be violated.

### Step 3: Audit Skills

Read all files in `.claude/skills/`. For each skill check:

- **Name**: Must be kebab-case, match folder name, no spaces or capitals.
- **Description**: Must include BOTH what it does AND when to use it (trigger phrases users would actually say).
- **Description length**: Under 1024 characters, no XML tags.
- **Instructions**: Specific and actionable, not vague. Use numbered steps and bullet points.
- **Error handling**: Includes what to do when things fail.
- **Progressive disclosure**: Core instructions in SKILL.md, detailed docs in `references/` if needed. Keep SKILL.md under 5,000 words.
- **No over-triggering**: Description is specific enough to not trigger on unrelated tasks. Add negative triggers if needed ("Do NOT use for...").
- **No under-triggering**: Description includes paraphrased trigger phrases users might say.

### Step 4: Audit Agents

Read all files in `.claude/agents/`. For each agent check:

- **Model selection**: Use the cheapest model that works (haiku for simple reads/searches, sonnet for code review, opus only for complex reasoning).
- **Tool access**: Only the tools actually needed — no broader access than necessary.
- **Focused scope**: Clear, bounded prompt with termination criteria. Agents should not explore indefinitely.
- **Output format**: Specifies what the agent should return (not open-ended).

### Step 5: Audit Settings and CI

- **`.claude/settings.json`**: Are permissions appropriate? Any missing safe commands causing repeated approval prompts? Any overly broad patterns?
- **`.github/workflows/ci.yml`**: Does CI cover lint, typecheck, and tests? Are jobs parallelized?
- **`pyproject.toml`**: Are linting rules, test config, and tooling current?

### Step 6: Compare and Apply

For each gap found:
1. Determine if the fix is worth the change (don't rewrite working config for aesthetics)
2. Apply the fix with a concrete edit
3. Every change must have a clear "why"

CRITICAL: Be surgical. Only change what actually improves effectiveness or addresses a real gap.

### Step 7: Log Changes

Append to `.claude/improvements.log`:
```
[DATE] CHANGE: what was changed | WHY: reason | PRACTICE: which best practice it addresses
```

### Step 8: Verify

Run in sequence:
1. `uv run ruff check .` — must pass
2. `uv run mypy src/` — must pass
3. `uv run pytest` — must pass

If any fail, fix before completing.

## Troubleshooting

**No changes needed**: If everything passes audit, log `[DATE] AUDIT: No changes needed — all config up to date` and report to user.

**WebFetch fails**: If the best practices page can't be fetched, audit against the known practices already embedded in this skill. Note in the log that the fetch failed.

**Breaking changes**: If an improvement breaks tests or lint, revert it immediately. Log the attempted change and why it failed.

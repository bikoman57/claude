# Project: Financial Analysis Agents

## Build & Run
- `uv sync` to install dependencies
- `uv run python -m app` to run the application
- `uv run pytest` to run all tests
- `uv run pytest tests/test_specific.py::test_name` to run a single test
- `uv run ruff check .` to lint
- `uv run ruff format .` to format
- `uv run mypy src/` to typecheck

## Code Style
- Python 3.12+, use modern syntax (type hints, match statements, f-strings)
- Use `from __future__ import annotations` in all modules
- Prefer dataclasses or Pydantic models over raw dicts
- Use `pathlib.Path` instead of `os.path`

## Testing
- Run single tests during development, full suite before committing
- IMPORTANT: Always run tests after making changes to verify nothing is broken

## Git Workflow
- Branch naming: `feature/<name>`, `fix/<name>`, `chore/<name>`
- Commit messages: imperative mood, concise (<72 chars first line)
- Always create a PR for review — never push directly to main

## Architecture
- Leveraged ETF mean-reversion swing trading system with orchestrated analysis
- **Strategy**: Monitor underlying index drawdowns from ATH → signal to buy leveraged ETF → take profit at target
- **Orchestration**: CIO (exec-cio) agent coordinates all departments, cross-references across domains, produces ONE unified report
- **Enterprise structure**: Board (you) > Executive (CIO, COO) > Departments (Trading, Research, Intelligence, Risk, Operations)
- **Org chart**: See `docs/org-chart.md` for full Mermaid diagram

### Sector-to-ETF Mapping
| Sector | Tickers | Leveraged ETF |
|--------|---------|---------------|
| Tech | AAPL, MSFT, GOOGL, META | TQQQ, TECL |
| Semiconductors | NVDA, AMD, AVGO | SOXL |
| Finance | JPM, GS, BAC | FAS |
| Energy | XOM, CVX | UCO |
| Biotech/Healthcare | LLY, PFE, JNJ | LABU |
| Broad Market / Small Cap | SPY, IWM | UPRO, TNA |

Geopolitical event categories: TRADE_WAR/TARIFF → tech, semis (TQQQ, SOXL, TECL) | MILITARY/SANCTIONS → energy, finance (UCO, FAS) | ELECTIONS/POLICY → broad, finance (UPRO, TNA, FAS) | TERRITORIAL (Taiwan) → semis (SOXL)

### Modules
- `src/app/etf/` — ETF universe, drawdown calc, signal state machine, confidence scoring, persistence
- `src/app/macro/` — VIX, FRED (CPI/GDP/unemployment), Fed rates/FOMC, Treasury yield curve
- `src/app/sec/` — SEC EDGAR filings, institutional 13F tracking, index holdings
- `src/app/risk/` — Portfolio risk limits, exposure calculations, veto logic
- `src/app/portfolio/` — Portfolio tracking, position sizing (fixed-fraction, Kelly criterion)
- `src/app/quant/` — Regime detection, recovery statistics, factor significance testing
- `src/app/history/` — Analysis snapshots, trade outcomes, factor weight learning
- `src/app/telegram/` — Telegram notifications and bidirectional messaging
- `src/app/news/` — Financial RSS feeds, article categorization, journalist accuracy tracking
- `src/app/geopolitical/` — GDELT events, geopolitical RSS, impact classification by sector
- `src/app/social/` — Reddit sentiment, Fed/SEC official statements, hawkish/dovish classification
- `src/app/statistics/` — Sector rotation, market breadth, cross-asset correlations, risk indicators
- `src/app/strategy/` — Backtesting engine, threshold optimization, strategy proposals
- `src/app/congress/` — Congressional stock trade disclosures (STOCK Act), member performance ratings, sector aggregation
- `src/app/polymarket/` — Polymarket prediction markets, crowd-sourced probability signals for Fed/geopolitical/economic events
- `src/app/scheduler/` — Daily runner, scheduled pre/post-market runs, HTML report publishing (GitHub Pages), Telegram delivery, Agile ceremony orchestration
- `src/app/agile/` — Sprint management, ceremonies (standup/planning/retro), roadmap OKRs, postmortem system
- `src/app/finops/` — Token cost tracking per agent, department budgets ($100/week), ROI analysis, reallocation suggestions
- `src/app/devops/` — Pipeline health scoring (A-F grade), module trends, 7-day success rates

### CLI Commands
See `.claude/references/cli-commands.md` for the full list. Key commands:
- `uv run python -m app.etf scan` — scan for drawdown signals
- `uv run python -m app.scheduler pre-market|post-market` — run scheduled analysis

### Agents (23 total, `{dept}-{role}` naming)
- **Executive**: exec-cio (opus), exec-coo (haiku)
- **Trading**: trading-drawdown-monitor, trading-market-analyst, trading-swing-screener
- **Research**: research-macro, research-sec, research-statistics, research-strategy-analyst, research-strategy-researcher (opus), research-quant (opus)
- **Intelligence**: intel-chief, intel-news, intel-geopolitical, intel-social, intel-congress
- **Risk**: risk-manager, risk-portfolio
- **Operations**: ops-code-reviewer (haiku), ops-design-reviewer, ops-security-reviewer (haiku), ops-token-optimizer (haiku), ops-devops (haiku)

### Skills
- `.claude/skills/` — unified-report, team-report, analyze-etf, scan-opportunities, market-report, intel-briefing, macro-check, risk-check, strategy-lab, research, ops-health, self-improve, fix-issue, new-module, telegram-notify, telegram-ask, telegram-setup

### Agent Teams (Experimental)
- Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json` (already enabled)
- `/team-report` — parallel daily report: CIO spawns 13 department teammates, all run simultaneously
- `/unified-report` — sequential fallback: CIO runs all modules one by one
- All domain analysts are team-aware: they broadcast key findings using `[DOMAIN] METRIC: value (assessment)` format
- Risk-manager has VETO authority over entry signals that exceed portfolio limits
- In-process mode only (Windows/VS Code) — use Shift+Up/Down to navigate teammates
- Higher token usage than solo mode, but significantly faster wall-clock time

### Data & State
- Signal lifecycle: WATCH → ALERT → SIGNAL → ACTIVE → TARGET
- Confidence scoring: 14 factors → HIGH/MEDIUM/LOW (drawdown, VIX, Fed, yields, SEC, fundamentals, prediction markets, earnings, geopolitical, social, news, statistics, congress, portfolio risk)
- Factor weight learning: track trade outcomes, compute predictive weights over time
- Runtime state persisted in `data/` (gitignored): signals.json, outcomes.json, history/, backtests/, scheduler_status.json, agile/, finops/, devops/, postmortems/
- Configuration via environment variables (see `.env`)
- Keep modules small and focused; prefer composition over inheritance

## Telegram Integration
- `uv run python -m app.telegram notify "message"` sends a notification
- `uv run python -m app.telegram ask "question"` asks and waits for reply (stdout)
- `uv run python -m app.telegram setup-check` verifies configuration
- Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Use `/telegram-notify`, `/telegram-ask` skills for agent integration

## Telegram Bot Listener (Remote Control)
- `uv run python -m app.telegram listen` starts the long-polling listener
- `--timeout SECONDS` sets Claude command timeout (default: 600s)
- `--claude PATH` overrides claude CLI path
- Commands: `/analyze <TICKER>`, `/report`, `/scan` (`/screen`), `/intel`, `/macro`, `/risk` (`/portfolio`), `/strategy [TICKER]`, `/research`, `/ops` (`/health`), `/help`, `/status`
- Free-form text is passed directly to `claude -p` for AI-powered handling
- Only processes messages from the configured `TELEGRAM_CHAT_ID` (security)
- Processes one command at a time; rejects concurrent with "still working" message
- Auto-start via Windows Scheduled Task (see plan file for setup script)

## Scheduled Runs (Windows Task Scheduler)
- **Pre-market** (7:00 AM ET, weekdays): standup ceremony + data pipeline + publish HTML + Claude analysis + Telegram + token/health tracking
- **Post-market** (4:30 PM ET, weekdays): data pipeline + publish HTML + Claude analysis + Telegram + token/health tracking + postmortem detection
- **Monday pre-market**: also runs sprint planning (auto-creates sprint if needed)
- **Friday post-market**: also runs sprint retrospective + auto-advances to next sprint
- Pre-market focuses on: overnight developments, entry signal assessment, strategy research, actionable price levels
- Post-market focuses on: daily review, position P&L, signal state changes, strategy deep-dive, overnight positioning
- Setup (run as Administrator): `powershell -ExecutionPolicy Bypass -File scripts\setup-scheduled-tasks.ps1`
- Remove tasks: `powershell -ExecutionPolicy Bypass -File scripts\setup-scheduled-tasks.ps1 -Remove`
- Logs stored in `data/logs/` (gitignored)
- Manual test: `uv run python -m app.scheduler pre-market` or `post-market`

## Environment Variables
- `TELEGRAM_BOT_TOKEN` — Telegram bot token (required for notifications)
- `TELEGRAM_CHAT_ID` — Telegram chat ID (required for notifications)
- `FRED_API_KEY` — FRED API key (optional, for macro data)
- `SEC_EDGAR_EMAIL` — Email for SEC EDGAR User-Agent (optional)
- `REDDIT_CLIENT_ID` — Reddit OAuth client ID (optional, for social module)
- `REDDIT_CLIENT_SECRET` — Reddit OAuth client secret (optional, for social module)
- `CLAUDE_EXECUTABLE` — Path to Claude CLI (auto-discovered if on PATH)
- `CLAUDE_ANALYSIS_TIMEOUT` — Seconds for Claude agent analysis (default: 3600)
- `UV_EXECUTABLE` — Path to uv (default: `C:\Users\texcu\.local\bin\uv.exe`)
- `SCHEDULER_PROJECT_DIR` — Override project directory path

## Token Discipline
- IMPORTANT: Use subagents for any exploration that reads more than 3 files — keep main context clean
- Run single tests (`pytest tests/test_foo.py::test_name`), not the full suite, during development
- Scope investigations narrowly: specify files/dirs, don't say "look at everything"
- Prefer `Glob` and `Grep` over reading entire files when you only need a specific section
- Use `haiku` model for subagents doing simple tasks (searching, linting, reviewing)
- When context gets noisy, suggest `/clear` and start fresh with a better prompt

### Planning and Invocation
- **Plan before acting**: outline which files to read and which commands to run BEFORE starting
- **Be specific in subagent prompts**: tell them exactly which files to read and what to look for
- **Batch CLI commands**: run related commands in a single tool call when possible
- **Cache awareness**: if you already have data from a CLI command in this session, do not re-run it
- **Provide context upfront**: include relevant background in initial messages to reduce back-and-forth

### Agent Cost Tiers
- **opus**: CIO synthesis, strategy research, quant analysis (complex reasoning only)
- **sonnet**: domain analysis, intel aggregation, design review (moderate reasoning)
- **haiku**: code review, security review, token audit, COO ops check (checklist/mechanical tasks)
- Default to haiku for subagents unless the task requires multi-step reasoning

## Self-Improvement
- Run `/self-improve` periodically to audit this project against latest best practices
- Use the `ops-token-optimizer` subagent to audit for token waste
- Improvements are tracked in `.claude/improvements.log`

## Common Gotchas
- Always use `uv run` prefix when running Python commands (ensures correct venv)
- Environment variables must be set before running — check `.env.example`

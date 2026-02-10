# Financial Analysis Agents

AI-powered financial analysis agents with real-time Telegram alerts. Claude Code agents analyze stocks, screen for signals, and report market conditions — notifying you on Telegram when they find something interesting.

## How It Works

This is not a traditional app. The intelligence lives in **Claude Code agents and skills**:

- **Agents** (`.claude/agents/`) do the analysis — market technicals, fundamentals, signal screening
- **Skills** (`.claude/skills/`) are workflows you invoke — analyze a stock, screen the market, get a daily report
- **Python modules** (`src/app/`) provide shared infrastructure — Telegram notifications, data formatting
- **Telegram bot** sends you real-time alerts and waits for your decisions

## Quick Start

```bash
git clone https://github.com/bikoman57/claude.git
cd claude
uv sync
```

Set up Telegram (one-time): run `/telegram-setup` in Claude Code.

## Usage

In Claude Code, use these skills:

| Skill | What it does |
|---|---|
| `/analyze-stock AAPL` | Full analysis: technicals + fundamentals + signals |
| `/screen-stocks` | Scan major stocks for trading signals |
| `/market-report` | Daily market summary with sector rotation |
| `/telegram-notify "message"` | Send alert to your phone |
| `/telegram-ask "question"` | Ask you a question, wait for reply |

## Agents

| Agent | Purpose | Model |
|---|---|---|
| `market-analyst` | Price action, technicals, trends | sonnet |
| `fundamentals-analyst` | Financials, valuation, earnings | sonnet |
| `signal-screener` | Trading signals, unusual activity | sonnet |
| `code-reviewer` | Code quality review | sonnet |
| `security-reviewer` | Security vulnerability audit | sonnet |
| `token-optimizer` | Token usage audit | haiku |

## Project Structure

```
.
├── CLAUDE.md                          # Agent conventions
├── .claude/
│   ├── agents/                        # Analysis agents
│   │   ├── market-analyst.md          # Technicals & price action
│   │   ├── fundamentals-analyst.md    # Financials & valuation
│   │   ├── signal-screener.md         # Signal screening
│   │   ├── code-reviewer.md           # Code review
│   │   ├── security-reviewer.md       # Security audit
│   │   └── token-optimizer.md         # Token waste audit
│   ├── skills/                        # User-facing workflows
│   │   ├── analyze-stock/             # /analyze-stock <ticker>
│   │   ├── screen-stocks/             # /screen-stocks [tickers]
│   │   ├── market-report/             # /market-report
│   │   ├── telegram-notify/           # /telegram-notify <msg>
│   │   ├── telegram-ask/              # /telegram-ask <question>
│   │   ├── telegram-setup/            # /telegram-setup
│   │   ├── fix-issue/                 # /fix-issue <number>
│   │   ├── new-module/                # /new-module <name>
│   │   └── self-improve/              # /self-improve
│   └── settings.json                  # Permission allowlists
├── .github/workflows/ci.yml           # CI pipeline
├── src/app/
│   ├── telegram/                      # Telegram bot (notify + ask)
│   └── __main__.py                    # Entry point
├── tests/                             # 20 tests
└── pyproject.toml                     # Dependencies & tooling
```

## Development

```bash
uv run pytest              # Run tests
uv run ruff check .        # Lint
uv run mypy src/           # Type check
```

## Disclaimer

This project is for informational and educational purposes only. It is not financial advice. Always do your own research before making investment decisions.

# App

Production Python application.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended package manager)

## Setup

```bash
# Clone the repository
git clone https://github.com/bikoman57/claude.git
cd claude

# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env
# Edit .env with your values
```

## Development

```bash
# Run the application
uv run python -m app

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src/
```

## Project Structure

```
.
├── CLAUDE.md                # Claude Code project conventions
├── .claude/
│   ├── settings.json        # Permission allowlists
│   ├── skills/              # Reusable Claude workflows
│   │   ├── fix-issue/       # /fix-issue <number>
│   │   └── new-module/      # /new-module <name>
│   └── agents/              # Specialized subagents
│       ├── security-reviewer.md
│       └── code-reviewer.md
├── .github/workflows/
│   └── ci.yml               # Lint, typecheck, test pipeline
├── src/app/                  # Application source code
│   ├── __init__.py
│   └── __main__.py          # Entry point
├── tests/                    # Test suite
│   ├── conftest.py
│   └── test_main.py
├── pyproject.toml            # Project config (deps, ruff, pytest, mypy)
└── .env.example              # Environment variable template
```

## Git Workflow

- Branch from `main` using `feature/<name>`, `fix/<name>`, or `chore/<name>`
- Open a PR for all changes -- never push directly to `main`
- CI runs lint, typecheck, and tests on every PR

# Project: Claude

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
- Imports: stdlib first, then third-party, then local (enforced by ruff isort)
- Prefer dataclasses or Pydantic models over raw dicts
- Use `pathlib.Path` instead of `os.path`
- Async code uses `asyncio` — no callbacks

## Testing
- Use pytest with fixtures; no unittest.TestCase
- Prefer `pytest.raises` for exception testing
- Name test files `test_<module>.py`, test functions `test_<behavior>`
- Run single tests during development, full suite before committing
- IMPORTANT: Always run tests after making changes to verify nothing is broken

## Git Workflow
- Branch naming: `feature/<name>`, `fix/<name>`, `chore/<name>`
- Commit messages: imperative mood, concise (<72 chars first line)
- Always create a PR for review — never push directly to main

## Architecture
- Source code lives in `src/app/`
- Entry point: `src/app/__main__.py`
- Configuration via environment variables (see `.env.example`)
- Keep modules small and focused; prefer composition over inheritance

## Telegram Integration
- `uv run python -m app.telegram notify "message"` sends a notification
- `uv run python -m app.telegram ask "question"` asks and waits for reply (stdout)
- `uv run python -m app.telegram setup-check` verifies configuration
- Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Use `/telegram-notify`, `/telegram-ask` skills for agent integration

## Token Discipline
- IMPORTANT: Use subagents for any exploration that reads more than 3 files — keep main context clean
- Run single tests (`pytest tests/test_foo.py::test_name`), not the full suite, during development
- Scope investigations narrowly: specify files/dirs, don't say "look at everything"
- Prefer `Glob` and `Grep` over reading entire files when you only need a specific section
- Use `haiku` model for subagents doing simple tasks (searching, linting, reviewing)
- When context gets noisy, suggest `/clear` and start fresh with a better prompt

## Self-Improvement
- Run `/self-improve` periodically to audit this project against latest best practices
- Use the `token-optimizer` subagent to audit for token waste
- Improvements are tracked in `.claude/improvements.log`

## Common Gotchas
- Always use `uv run` prefix when running Python commands (ensures correct venv)
- Environment variables must be set before running — check `.env.example`

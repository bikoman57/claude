---
name: new-module
description: Scaffold a new Python module with tests following project conventions. Use when user says "new module", "create module", "add module", or "scaffold".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.1.0
  category: workflow-automation
---

# Scaffold New Module

Create a new module named $ARGUMENTS following project conventions.

## Instructions

### Step 1: Create the Module
Create `src/app/$ARGUMENTS.py` with:
- `from __future__ import annotations` at the top
- Type hints on all public functions
- Dataclasses or Pydantic models for structured data (not raw dicts)
- `pathlib.Path` instead of `os.path`

### Step 2: Create Tests
Create `tests/test_$ARGUMENTS.py` with:
- `from __future__ import annotations` at the top
- At least one smoke test for the main functionality
- Use pytest fixtures, not unittest.TestCase

### Step 3: Verify
```bash
uv run pytest tests/test_$ARGUMENTS.py -v
uv run ruff check src/app/$ARGUMENTS.py tests/test_$ARGUMENTS.py
uv run mypy src/app/$ARGUMENTS.py
```

All three must pass before reporting completion.

## Troubleshooting

**Import errors**: Ensure the module is importable via `from app.$ARGUMENTS import ...`. Check that `src/app/__init__.py` exists.

**mypy errors**: All public functions need return type annotations. Use `-> None` for functions that don't return a value.

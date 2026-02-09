---
name: fix-issue
description: Analyze and fix a GitHub issue end-to-end. Use when user says "fix issue", "fix bug #123", "resolve issue", or provides a GitHub issue number to work on.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.1.0
  category: workflow-automation
---

# Fix GitHub Issue

Analyze and fix the GitHub issue: $ARGUMENTS

## Instructions

### Step 1: Understand the Issue
Run `gh issue view $ARGUMENTS` to get the full issue details.
Read the title, description, labels, and any comments.

### Step 2: Investigate
Use a subagent to search the codebase for files related to the issue. Scope the search narrowly based on the issue description.

### Step 3: Create a Branch
```bash
git checkout -b fix/$ARGUMENTS-short-description
```

### Step 4: Implement the Fix
Make the necessary code changes. Follow existing patterns in the codebase.

### Step 5: Write Tests
Write a failing test that reproduces the issue, then verify your fix makes it pass.
```bash
uv run pytest tests/test_specific.py::test_name -v
```

### Step 6: Verify Quality
```bash
uv run ruff check .
uv run mypy src/
uv run pytest
```

### Step 7: Commit and PR
Create a descriptive commit and push the branch:
```bash
git add <changed files>
git commit -m "fix: <description> (closes #$ARGUMENTS)"
git push -u origin fix/$ARGUMENTS-short-description
gh pr create --title "Fix #$ARGUMENTS: <description>" --body "Closes #$ARGUMENTS"
```

## Troubleshooting

**Issue not found**: Verify the issue number is correct with `gh issue list`.

**Tests fail after fix**: The fix may be incomplete or introduce a regression. Review the failing test output carefully before adjusting.

**Lint/type errors**: Fix all errors before committing. Do not suppress warnings with noqa unless there is a clear reason.

---
name: telegram-ask
description: Ask the user a verification question on Telegram and wait for their reply. Use when user says "ask me on telegram", "verify with me", "get approval", or when an agent needs confirmation before a destructive or important action.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.1.0
  category: workflow-automation
---

# Telegram Verification

Ask a question on Telegram and wait for the user's reply. $ARGUMENTS

## Instructions

### Step 1: Send the Question
```bash
uv run python -m app.telegram ask $ARGUMENTS
```

Optional: Set a custom timeout (default 300 seconds):
```bash
uv run python -m app.telegram ask --timeout 120 "Approve this PR?"
```

### Step 2: Process the Reply
The user's reply is printed to stdout. Use it to decide next steps:
- Reply contains "yes", "approve", "proceed", "ok" → continue with the action
- Reply contains "no", "reject", "stop", "cancel" → abort and explain why
- Any other reply → treat as free-form instructions and follow them

### Step 3: Handle Timeout
If exit code is 2, no reply was received within the timeout.
Inform the user that the request timed out and suggest they check Telegram.

## Troubleshooting

**ValueError about missing environment variables**: Tell the user to run `/telegram-setup` first.

**Timeout too short**: Increase with `--timeout` flag (value in seconds).

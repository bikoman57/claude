---
name: telegram-notify
description: Send a one-way Telegram notification to the user. Use when user says "notify me", "send telegram", "telegram notify", or when an agent needs to report task completion or failure.
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.1.0
  category: workflow-automation
---

# Telegram Notification

Send a Telegram notification. $ARGUMENTS

## Instructions

### Step 1: Send the Message
```bash
uv run python -m app.telegram notify $ARGUMENTS
```

Optional: Add a custom title with `--title`:
```bash
uv run python -m app.telegram notify --title "Build" "All tests passed"
```

### Step 2: Confirm
If exit code is 0, the message was sent successfully.

## Troubleshooting

**ValueError about missing environment variables**: Tell the user to run `/telegram-setup` to configure their bot token and chat ID.

**HTTP error**: The Telegram API may be temporarily unavailable. Wait a moment and retry once.

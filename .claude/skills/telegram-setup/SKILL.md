---
name: telegram-setup
description: Guide the user through Telegram bot setup and configuration. Use when user says "setup telegram", "configure telegram", "telegram setup", or "connect telegram bot".
disable-model-invocation: true
metadata:
  author: bikoman57
  version: 1.1.0
  category: workflow-automation
---

# Telegram Bot Setup

Help the user set up Telegram bot integration.

## Instructions

### Step 1: Create the Bot
Tell the user to open Telegram and message **@BotFather**:
1. Send `/newbot`
2. Choose a display name (e.g., "MyClaude")
3. Choose a username ending in "bot" (e.g., "my_claude_bot")
4. Copy the bot token provided (format: `123456:ABC-xyz...`)

### Step 2: Get the Chat ID
Tell the user to:
1. Open their new bot in Telegram and send any message (e.g., "hello")
2. Then run this command to fetch their chat ID:

```bash
powershell -Command "Invoke-RestMethod -Uri 'https://api.telegram.org/bot<TOKEN>/getUpdates' | ConvertTo-Json -Depth 10"
```

Find the `chat.id` value in the JSON response under `result[0].message.chat.id`.

### Step 3: Configure Environment
Update `.env` in the project root:
```
TELEGRAM_BOT_TOKEN=<token from step 1>
TELEGRAM_CHAT_ID=<chat id from step 2>
```

### Step 4: Verify
```bash
uv run python -m app.telegram setup-check
```
Expected output: `OK: message sent successfully`
The user should also receive a test message on Telegram.

## Troubleshooting

**Empty getUpdates response**: The user hasn't sent a message to the bot yet. They must open the bot in Telegram and send at least one message first.

**setup-check fails with ValueError**: The `.env` file is missing `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID`. Verify they are uncommented and have values.

**setup-check fails with HTTP error**: The bot token is invalid. Double-check it was copied correctly from BotFather.

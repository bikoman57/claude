from __future__ import annotations

import asyncio
import sys

from app.telegram.client import TelegramClient
from app.telegram.config import TelegramConfig
from app.telegram.formatting import (
    escape_markdown,
    notification_message,
    question_message,
)

USAGE = """\
Usage:
  uv run python -m app.telegram notify <message> [--title TITLE]
  uv run python -m app.telegram ask <question> [--timeout SECONDS]
  uv run python -m app.telegram setup-check
"""


async def cmd_notify(args: list[str]) -> int:
    """Send a one-way notification."""
    title = "Notification"
    message_parts: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        else:
            message_parts.append(args[i])
            i += 1

    if not message_parts:
        print("Error: message is required", file=sys.stderr)  # noqa: T201
        return 1

    text = notification_message(title, " ".join(message_parts))
    config = TelegramConfig.from_env()
    async with TelegramClient(config) as client:
        await client.send_message(text)
    return 0


async def cmd_ask(args: list[str]) -> int:
    """Send a question and wait for a reply."""
    timeout = 300
    question_parts: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--timeout" and i + 1 < len(args):
            timeout = int(args[i + 1])
            i += 2
        else:
            question_parts.append(args[i])
            i += 1

    if not question_parts:
        print("Error: question is required", file=sys.stderr)  # noqa: T201
        return 1

    question = " ".join(question_parts)
    text = question_message(question, hint="Reply to this message to answer\\.")
    config = TelegramConfig.from_env()
    async with TelegramClient(config) as client:
        try:
            reply = await client.ask_and_wait(text, timeout_seconds=timeout)
        except TimeoutError:
            print("Error: timed out waiting for reply", file=sys.stderr)  # noqa: T201
            return 2
    print(reply)  # noqa: T201
    return 0


async def cmd_setup_check() -> int:
    """Verify the bot token and chat_id work."""
    config = TelegramConfig.from_env()
    async with TelegramClient(config) as client:
        result = await client.send_message(
            escape_markdown("Setup check: Telegram integration is working.")
        )
    if result.get("ok"):
        print("OK: message sent successfully")  # noqa: T201
        return 0
    print(f"Error: {result}", file=sys.stderr)  # noqa: T201
    return 1


def main() -> None:
    if len(sys.argv) < 2:
        print(USAGE, file=sys.stderr)  # noqa: T201
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    match command:
        case "notify":
            exit_code = asyncio.run(cmd_notify(args))
        case "ask":
            exit_code = asyncio.run(cmd_ask(args))
        case "setup-check":
            exit_code = asyncio.run(cmd_setup_check())
        case _:
            print(f"Unknown command: {command}", file=sys.stderr)  # noqa: T201
            print(USAGE, file=sys.stderr)  # noqa: T201
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

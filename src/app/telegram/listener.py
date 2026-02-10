from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from dataclasses import dataclass, field
from typing import Any

from app.telegram.client import TelegramClient
from app.telegram.config import TelegramConfig
from app.telegram.dispatcher import CommandDispatcher, ParsedCommand
from app.telegram.formatting import escape_markdown

logger = logging.getLogger(__name__)


@dataclass
class BotListener:
    """Long-polling Telegram bot listener."""

    client: TelegramClient
    dispatcher: CommandDispatcher
    config: TelegramConfig
    poll_timeout: int = 30
    _running: bool = field(default=False, init=False, repr=False)
    _busy: bool = field(default=False, init=False, repr=False)

    async def run(self) -> None:
        """Main polling loop. Runs until stopped."""
        self._running = True
        logger.info("Bot listener started. Polling for messages...")

        try:
            while self._running:
                try:
                    updates = await self.client.get_updates(
                        timeout=self.poll_timeout,
                    )
                    for update in updates:
                        await self._process_update(update)
                except Exception:
                    if not self._running:
                        break
                    logger.exception("Error during polling cycle")
                    await asyncio.sleep(5.0)
        finally:
            logger.info("Bot listener stopped.")

    def stop(self) -> None:
        """Signal the listener to stop after the current cycle."""
        self._running = False

    async def _process_update(self, update: dict[str, Any]) -> None:
        """Process a single update, filtering by chat_id."""
        message: dict[str, Any] = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")

        # Only process messages from the authorized chat
        if chat_id != self.config.chat_id:
            logger.debug("Ignoring message from unauthorized chat: %s", chat_id)
            return

        if not text:
            return

        logger.info("Received command: %s", text[:80])

        # Reject concurrent commands
        if self._busy:
            busy_msg = escape_markdown(
                "Still working on the previous command. Please wait.",
            )
            await self.client.send_message(busy_msg)
            return

        self._busy = True
        try:
            command = ParsedCommand.parse(text)
            await self.dispatcher.dispatch(command)
        except Exception:
            logger.exception("Error dispatching command: %s", text[:80])
            await self.client.send_message(
                escape_markdown("An internal error occurred. Check the bot logs."),
            )
        finally:
            self._busy = False


async def start_listener(
    *,
    project_dir: str,
    claude_executable: str = "claude",
    command_timeout: float = 600.0,
    poll_timeout: int = 30,
) -> None:
    """Initialize and start the bot listener with graceful shutdown."""
    config = TelegramConfig.from_env()

    async with TelegramClient(config) as client:
        dispatcher = CommandDispatcher(
            client=client,
            project_dir=project_dir,
            claude_executable=claude_executable,
            command_timeout=command_timeout,
        )
        listener = BotListener(
            client=client,
            dispatcher=dispatcher,
            config=config,
            poll_timeout=poll_timeout,
        )

        # Graceful shutdown via signals (best-effort on Windows)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError, OSError):
                loop.add_signal_handler(sig, listener.stop)

        startup_msg = escape_markdown(
            "Bot listener started. Send /help for commands.",
        )
        await client.send_message(startup_msg)

        await listener.run()

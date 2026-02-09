from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.telegram.config import TelegramConfig


@dataclass
class TelegramClient:
    """Async Telegram Bot API client for sending messages and polling replies."""

    config: TelegramConfig
    _http: httpx.AsyncClient = field(init=False, repr=False)
    _offset_file: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._offset_file = Path.home() / ".telegram_bot_offset"

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> TelegramClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def send_message(
        self,
        text: str,
        *,
        parse_mode: str = "MarkdownV2",
    ) -> dict[str, Any]:
        """Send a message to the configured chat."""
        url = f"{self.config.base_url}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self.config.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        response = await self._http.post(url, json=payload)
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def get_updates(
        self,
        *,
        timeout: int = 30,
    ) -> list[dict[str, Any]]:
        """Long-poll for updates from the bot."""
        url = f"{self.config.base_url}/getUpdates"
        offset = self._load_offset()
        params: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        response = await self._http.post(
            url,
            json=params,
            timeout=httpx.Timeout(timeout + 10.0),
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        updates: list[dict[str, Any]] = data.get("result", [])
        if updates:
            last_id: int = updates[-1]["update_id"]
            self._save_offset(last_id + 1)
        return updates

    async def ask_and_wait(
        self,
        question_text: str,
        *,
        timeout_seconds: int = 300,
        poll_interval: int = 30,
    ) -> str:
        """Send a question, poll for a reply, return the reply text."""
        await self.send_message(question_text)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            remaining = int(deadline - time.monotonic())
            poll_time = min(poll_interval, max(remaining, 1))
            updates = await self.get_updates(timeout=poll_time)
            for update in updates:
                message: dict[str, Any] = update.get("message", {})
                chat_id = str(message.get("chat", {}).get("id", ""))
                if chat_id == self.config.chat_id and "text" in message:
                    return str(message["text"])
        msg = f"No reply received within {timeout_seconds} seconds"
        raise TimeoutError(msg)

    def _load_offset(self) -> int | None:
        if self._offset_file.exists():
            return int(self._offset_file.read_text().strip())
        return None

    def _save_offset(self, offset: int) -> None:
        self._offset_file.write_text(str(offset))

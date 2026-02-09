from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class TelegramConfig:
    """Telegram bot configuration loaded from environment variables."""

    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> TelegramConfig:
        load_dotenv()
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not bot_token:
            msg = "TELEGRAM_BOT_TOKEN environment variable is required"
            raise ValueError(msg)
        if not chat_id:
            msg = "TELEGRAM_CHAT_ID environment variable is required"
            raise ValueError(msg)
        return cls(bot_token=bot_token, chat_id=chat_id)

    @property
    def base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}"

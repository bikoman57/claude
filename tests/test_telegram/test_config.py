from __future__ import annotations

import pytest

from app.telegram.config import TelegramConfig


def test_from_env_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")
    config = TelegramConfig.from_env()
    assert config.bot_token == "123:ABC"
    assert config.chat_id == "456"


def test_from_env_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        TelegramConfig.from_env()


def test_from_env_missing_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    with pytest.raises(ValueError, match="TELEGRAM_CHAT_ID"):
        TelegramConfig.from_env()


def test_base_url() -> None:
    config = TelegramConfig(bot_token="123:ABC", chat_id="456")
    assert config.base_url == "https://api.telegram.org/bot123:ABC"

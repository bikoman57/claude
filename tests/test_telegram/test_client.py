from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.telegram.client import TelegramClient
from app.telegram.config import TelegramConfig


@pytest.fixture
def config() -> TelegramConfig:
    return TelegramConfig(bot_token="test-token", chat_id="12345")


@pytest.fixture
def client(config: TelegramConfig, tmp_path: Path) -> TelegramClient:
    c = TelegramClient(config)
    c._offset_file = tmp_path / "offset"
    return c


def _mock_response(data: dict) -> MagicMock:  # type: ignore[type-arg]
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


async def test_send_message(client: TelegramClient) -> None:
    mock_resp = _mock_response({"ok": True, "result": {}})
    with patch.object(
        client._http, "post", new_callable=AsyncMock, return_value=mock_resp
    ):
        result = await client.send_message("hello")
    assert result["ok"] is True


async def test_get_updates_saves_offset(client: TelegramClient) -> None:
    mock_resp = _mock_response(
        {"ok": True, "result": [{"update_id": 100, "message": {"text": "hi"}}]}
    )
    with patch.object(
        client._http, "post", new_callable=AsyncMock, return_value=mock_resp
    ):
        updates = await client.get_updates(timeout=1)
    assert len(updates) == 1
    assert client._offset_file.read_text() == "101"


async def test_get_updates_empty(client: TelegramClient) -> None:
    mock_resp = _mock_response({"ok": True, "result": []})
    with patch.object(
        client._http, "post", new_callable=AsyncMock, return_value=mock_resp
    ):
        updates = await client.get_updates(timeout=1)
    assert updates == []
    assert not client._offset_file.exists()


async def test_ask_and_wait_returns_reply(client: TelegramClient) -> None:
    send_resp = _mock_response({"ok": True, "result": {}})
    update_resp = _mock_response(
        {
            "ok": True,
            "result": [
                {
                    "update_id": 200,
                    "message": {"text": "yes", "chat": {"id": 12345}},
                }
            ],
        }
    )
    with patch.object(
        client._http,
        "post",
        new_callable=AsyncMock,
        side_effect=[send_resp, update_resp],
    ):
        reply = await client.ask_and_wait(
            "continue?", timeout_seconds=5, poll_interval=1
        )
    assert reply == "yes"


async def test_ask_and_wait_ignores_other_chats(
    client: TelegramClient,
) -> None:
    send_resp = _mock_response({"ok": True, "result": {}})
    wrong_chat_resp = _mock_response(
        {
            "ok": True,
            "result": [
                {
                    "update_id": 300,
                    "message": {"text": "wrong", "chat": {"id": 99999}},
                }
            ],
        }
    )
    right_chat_resp = _mock_response(
        {
            "ok": True,
            "result": [
                {
                    "update_id": 301,
                    "message": {"text": "correct", "chat": {"id": 12345}},
                }
            ],
        }
    )
    with patch.object(
        client._http,
        "post",
        new_callable=AsyncMock,
        side_effect=[send_resp, wrong_chat_resp, right_chat_resp],
    ):
        reply = await client.ask_and_wait(
            "continue?", timeout_seconds=10, poll_interval=1
        )
    assert reply == "correct"


async def test_offset_persistence(client: TelegramClient) -> None:
    client._save_offset(42)
    assert client._load_offset() == 42


async def test_offset_missing(client: TelegramClient) -> None:
    assert client._load_offset() is None

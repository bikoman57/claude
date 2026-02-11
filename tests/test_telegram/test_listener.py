from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.telegram.client import TelegramClient
from app.telegram.config import TelegramConfig
from app.telegram.dispatcher import CommandDispatcher
from app.telegram.listener import BotListener

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> TelegramConfig:
    return TelegramConfig(bot_token="test-token", chat_id="12345")


@pytest.fixture
def client(config: TelegramConfig, tmp_path: Path) -> TelegramClient:
    c = TelegramClient(config)
    c._offset_file = tmp_path / "offset"
    return c


@pytest.fixture
def dispatcher(client: TelegramClient) -> CommandDispatcher:
    return CommandDispatcher(
        client=client,
        project_dir="/fake/project",
        command_timeout=5.0,
    )


@pytest.fixture
def listener(
    client: TelegramClient,
    dispatcher: CommandDispatcher,
    config: TelegramConfig,
) -> BotListener:
    return BotListener(client=client, dispatcher=dispatcher, config=config)


# ---------------------------------------------------------------------------
# _process_update tests
# ---------------------------------------------------------------------------


class TestProcessUpdate:
    async def test_authorized_chat_dispatches(self, listener: BotListener) -> None:
        update = {
            "update_id": 100,
            "message": {"text": "/help", "chat": {"id": 12345}},
        }
        with patch.object(
            listener.dispatcher, "dispatch", new_callable=AsyncMock
        ) as mock:
            await listener._process_update(update)
        mock.assert_called_once()

    async def test_unauthorized_chat_ignored(self, listener: BotListener) -> None:
        update = {
            "update_id": 100,
            "message": {"text": "/help", "chat": {"id": 99999}},
        }
        with patch.object(
            listener.dispatcher, "dispatch", new_callable=AsyncMock
        ) as mock:
            await listener._process_update(update)
        mock.assert_not_called()

    async def test_no_text_ignored(self, listener: BotListener) -> None:
        update = {
            "update_id": 100,
            "message": {"chat": {"id": 12345}},
        }
        with patch.object(
            listener.dispatcher, "dispatch", new_callable=AsyncMock
        ) as mock:
            await listener._process_update(update)
        mock.assert_not_called()

    async def test_empty_message_ignored(self, listener: BotListener) -> None:
        update = {"update_id": 100}
        with patch.object(
            listener.dispatcher, "dispatch", new_callable=AsyncMock
        ) as mock:
            await listener._process_update(update)
        mock.assert_not_called()

    async def test_busy_rejects_concurrent(self, listener: BotListener) -> None:
        listener._busy = True
        update = {
            "update_id": 100,
            "message": {"text": "/analyze AAPL", "chat": {"id": 12345}},
        }
        with (
            patch.object(
                listener.client, "send_message", new_callable=AsyncMock
            ) as mock_send,
            patch.object(
                listener.dispatcher, "dispatch", new_callable=AsyncMock
            ) as mock_dispatch,
        ):
            mock_send.return_value = {"ok": True}
            await listener._process_update(update)

        mock_dispatch.assert_not_called()
        mock_send.assert_called_once()
        assert (
            "working" in mock_send.call_args[0][0].lower()
            or "wait" in mock_send.call_args[0][0].lower()
        )

    async def test_dispatch_error_sends_error_message(
        self, listener: BotListener
    ) -> None:
        update = {
            "update_id": 100,
            "message": {"text": "/analyze AAPL", "chat": {"id": 12345}},
        }
        with (
            patch.object(
                listener.dispatcher,
                "dispatch",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(
                listener.client, "send_message", new_callable=AsyncMock
            ) as mock_send,
        ):
            mock_send.return_value = {"ok": True}
            await listener._process_update(update)

        mock_send.assert_called_once()
        assert listener._busy is False


# ---------------------------------------------------------------------------
# run loop tests
# ---------------------------------------------------------------------------


class TestRunLoop:
    async def test_stop_halts_loop(self, listener: BotListener) -> None:
        call_count = 0

        async def fake_get_updates(*, timeout: int = 30) -> list:  # type: ignore[type-arg]
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                listener.stop()
            return []

        with patch.object(listener.client, "get_updates", side_effect=fake_get_updates):
            await listener.run()

        assert call_count >= 2

    async def test_polling_error_does_not_crash(self, listener: BotListener) -> None:
        call_count = 0

        async def flaky_get_updates(*, timeout: int = 30) -> list:  # type: ignore[type-arg]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "network error"
                raise ConnectionError(msg)
            listener.stop()
            return []

        with (
            patch.object(listener.client, "get_updates", side_effect=flaky_get_updates),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await listener.run()

        assert call_count >= 2

    async def test_processes_updates_from_poll(self, listener: BotListener) -> None:
        updates = [
            {
                "update_id": 1,
                "message": {"text": "/help", "chat": {"id": 12345}},
            },
        ]
        call_count = 0

        async def get_updates_once(*, timeout: int = 30) -> list:  # type: ignore[type-arg]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return updates
            listener.stop()
            return []

        with (
            patch.object(listener.client, "get_updates", side_effect=get_updates_once),
            patch.object(
                listener.dispatcher, "dispatch", new_callable=AsyncMock
            ) as mock_dispatch,
        ):
            await listener.run()

        mock_dispatch.assert_called_once()

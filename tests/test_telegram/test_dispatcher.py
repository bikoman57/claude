from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.telegram.client import TelegramClient
from app.telegram.config import TelegramConfig
from app.telegram.dispatcher import (
    CommandDispatcher,
    CommandResult,
    ParsedCommand,
    split_message,
)

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
        claude_executable="claude",
        command_timeout=5.0,
    )


# ---------------------------------------------------------------------------
# ParsedCommand.parse tests
# ---------------------------------------------------------------------------


class TestParsedCommand:
    def test_parse_analyze(self) -> None:
        cmd = ParsedCommand.parse("/analyze AAPL")
        assert cmd.command == "analyze"
        assert cmd.arguments == "AAPL"

    def test_parse_analyze_with_bot_suffix(self) -> None:
        cmd = ParsedCommand.parse("/analyze@MyBot AAPL")
        assert cmd.command == "analyze"
        assert cmd.arguments == "AAPL"

    def test_parse_report_no_args(self) -> None:
        cmd = ParsedCommand.parse("/report")
        assert cmd.command == "report"
        assert cmd.arguments == ""

    def test_parse_screen_multiple_tickers(self) -> None:
        cmd = ParsedCommand.parse("/screen AAPL MSFT GOOGL")
        assert cmd.command == "screen"
        assert cmd.arguments == "AAPL MSFT GOOGL"

    def test_parse_help(self) -> None:
        cmd = ParsedCommand.parse("/help")
        assert cmd.command == "help"

    def test_parse_status(self) -> None:
        cmd = ParsedCommand.parse("/status")
        assert cmd.command == "status"

    def test_parse_unknown_slash_command(self) -> None:
        cmd = ParsedCommand.parse("/foobar hello")
        assert cmd.command == "foobar"
        assert cmd.arguments == "hello"

    def test_parse_plain_text(self) -> None:
        cmd = ParsedCommand.parse("what do you think about NVDA?")
        assert cmd.command == ""
        assert cmd.arguments == "what do you think about NVDA?"

    def test_parse_preserves_raw_text(self) -> None:
        cmd = ParsedCommand.parse("/analyze AAPL")
        assert cmd.raw_text == "/analyze AAPL"

    def test_parse_strips_whitespace(self) -> None:
        cmd = ParsedCommand.parse("  /help  ")
        assert cmd.command == "help"

    def test_parse_case_insensitive_command(self) -> None:
        cmd = ParsedCommand.parse("/ANALYZE AAPL")
        assert cmd.command == "analyze"


# ---------------------------------------------------------------------------
# split_message tests
# ---------------------------------------------------------------------------


class TestSplitMessage:
    def test_short_message(self) -> None:
        assert split_message("hello") == ["hello"]

    def test_exact_limit(self) -> None:
        text = "x" * 4096
        assert split_message(text) == [text]

    def test_split_at_line_boundary(self) -> None:
        lines = ["x" * 100] * 50  # 50 lines x 101 chars each (including \n)
        text = "\n".join(lines)
        chunks = split_message(text, max_length=500)
        for chunk in chunks:
            assert len(chunk) <= 500
        # Reassembled content should match original
        assert "\n".join(chunks) == text

    def test_single_long_line(self) -> None:
        text = "x" * 10000
        chunks = split_message(text, max_length=4096)
        assert all(len(c) <= 4096 for c in chunks)
        assert "".join(chunks) == text

    def test_preserves_content(self) -> None:
        text = "line1\nline2\nline3"
        assert split_message(text, max_length=5000) == [text]

    def test_empty_string(self) -> None:
        assert split_message("") == [""]


# ---------------------------------------------------------------------------
# CommandDispatcher._run_claude tests
# ---------------------------------------------------------------------------


class TestRunClaude:
    async def test_success(self, dispatcher: CommandDispatcher) -> None:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Analysis result", b"")
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await dispatcher._run_claude("analyze AAPL")

        assert result.success is True
        assert result.output == "Analysis result"
        assert result.exit_code == 0

    async def test_nonzero_exit(self, dispatcher: CommandDispatcher) -> None:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"partial output", b"some error")
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await dispatcher._run_claude("bad command")

        assert result.success is False
        assert "partial output" in result.output
        assert "some error" in result.output

    async def test_empty_output(self, dispatcher: CommandDispatcher) -> None:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await dispatcher._run_claude("quiet command")

        assert result.output == "(no output)"

    async def test_timeout(self, dispatcher: CommandDispatcher) -> None:
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = TimeoutError
        mock_process.kill = AsyncMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await dispatcher._run_claude("long task")

        assert result.success is False
        assert "timed out" in result.output

    async def test_cli_not_found(self, dispatcher: CommandDispatcher) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError,
        ):
            result = await dispatcher._run_claude("anything")

        assert result.success is False
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# CommandDispatcher.dispatch tests
# ---------------------------------------------------------------------------


class TestDispatch:
    async def test_help_sends_command_list(
        self, dispatcher: CommandDispatcher
    ) -> None:
        with patch.object(
            dispatcher.client, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"ok": True}
            await dispatcher.dispatch(ParsedCommand.parse("/help"))

        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "/analyze" in text

    async def test_status_responds(self, dispatcher: CommandDispatcher) -> None:
        with patch.object(
            dispatcher.client, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"ok": True}
            await dispatcher.dispatch(ParsedCommand.parse("/status"))

        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "running" in text.lower()

    async def test_analyze_sends_ack_then_result(
        self, dispatcher: CommandDispatcher
    ) -> None:
        result = CommandResult(success=True, output="AAPL looks good", exit_code=0)
        with (
            patch.object(
                dispatcher.client, "send_message", new_callable=AsyncMock
            ) as mock_send,
            patch.object(dispatcher, "_run_claude", return_value=result),
        ):
            mock_send.return_value = {"ok": True}
            await dispatcher.dispatch(ParsedCommand.parse("/analyze AAPL"))

        # First call = ack, second call = result
        assert mock_send.call_count == 2

    async def test_freeform_text_dispatched(
        self, dispatcher: CommandDispatcher
    ) -> None:
        result = CommandResult(success=True, output="Here's info", exit_code=0)
        with (
            patch.object(
                dispatcher.client, "send_message", new_callable=AsyncMock
            ) as mock_send,
            patch.object(dispatcher, "_run_claude", return_value=result) as mock_run,
        ):
            mock_send.return_value = {"ok": True}
            await dispatcher.dispatch(
                ParsedCommand.parse("what's going on with NVDA?")
            )

        # Claude should receive the raw text
        mock_run.assert_called_once_with("what's going on with NVDA?")

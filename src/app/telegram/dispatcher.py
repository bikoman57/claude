from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.telegram.formatting import bold, escape_markdown

if TYPE_CHECKING:
    from app.telegram.client import TelegramClient

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096

# Tools to pre-approve for headless Claude CLI runs.
_ALLOWED_TOOLS: list[str] = [
    "Bash(uv run*)",
    "Bash(uv sync*)",
    "Bash(git *)",
    "Bash(gh *)",
    "Bash(powershell*)",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "TodoWrite",
    "Task",
]

# Mapping of bot commands to Claude skill prompts
_COMMAND_SKILLS: dict[str, str] = {
    "analyze": "Use /analyze-stock",
    "report": "Use /market-report",
    "screen": "Use /screen-stocks",
}


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    """A parsed Telegram bot command."""

    command: str
    arguments: str
    raw_text: str

    @classmethod
    def parse(cls, text: str) -> ParsedCommand:
        """Parse a raw message into a command.

        Handles /slash commands (with optional @BotName suffix) and plain text.
        """
        stripped = text.strip()
        if not stripped.startswith("/"):
            return cls(command="", arguments=stripped, raw_text=stripped)

        # Split "/command args" or "/command@BotName args"
        parts = stripped.split(maxsplit=1)
        cmd_part = parts[0][1:]  # remove leading /
        arguments = parts[1] if len(parts) > 1 else ""

        # Strip @BotName suffix if present
        if "@" in cmd_part:
            cmd_part = cmd_part.split("@", maxsplit=1)[0]

        return cls(command=cmd_part.lower(), arguments=arguments, raw_text=stripped)


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result from executing a command via Claude CLI."""

    success: bool
    output: str
    exit_code: int


def split_message(text: str, *, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split text into chunks at line boundaries, respecting max_length."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in text.split("\n"):
        # +1 accounts for the newline character we'll re-join with
        line_len = len(line) + 1
        if current_len + line_len > max_length and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_len = 0

        # Handle single lines longer than max_length
        if len(line) > max_length:
            for i in range(0, len(line), max_length):
                chunks.append(line[i : i + max_length])
            continue

        current_lines.append(line)
        current_len += line_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


@dataclass
class CommandDispatcher:
    """Dispatches parsed commands to Claude CLI and returns results."""

    client: TelegramClient
    project_dir: str
    claude_executable: str = "claude"
    command_timeout: float = 600.0

    async def dispatch(self, command: ParsedCommand) -> None:
        """Handle a parsed command end-to-end."""
        match command.command:
            case "help":
                await self._handle_help()
                return
            case "status":
                await self._handle_status()
                return
            case cmd if cmd in _COMMAND_SKILLS:
                skill = _COMMAND_SKILLS[cmd]
                prompt = f"{skill} {command.arguments}".strip()
            case _:
                # Free-form text or unknown /command — pass to Claude as-is
                prompt = command.raw_text

        # Acknowledge
        ack = f"{bold('Received')} {escape_markdown(command.raw_text)}"
        await self.client.send_message(ack)

        result = await self._run_claude(prompt)
        await self._send_result(result)

    async def _handle_help(self) -> None:
        lines = [
            "/analyze <TICKER> — Full stock analysis",
            "/report — Daily market summary",
            "/screen [TICKERS] — Screen for trading signals",
            "/status — Check if the bot is alive",
            "/help — Show this message",
            "",
            "Or send any text and Claude will handle it.",
        ]
        await self.client.send_message(escape_markdown("\n".join(lines)))

    async def _handle_status(self) -> None:
        await self.client.send_message(escape_markdown("Bot is running."))

    async def _run_claude(self, prompt: str) -> CommandResult:
        """Spawn ``claude -p "prompt"`` and capture output."""
        try:
            env = os.environ.copy()
            env.setdefault("CLAUDE_CODE_GIT_BASH_PATH", r"D:\Git\bin\bash.exe")

            cmd: list[str] = [self.claude_executable, "-p", prompt]
            for tool in _ALLOWED_TOOLS:
                cmd.extend(["--allowedTools", tool])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_dir,
                env=env,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=self.command_timeout,
            )
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode or 0

            output = stdout_text.strip()
            if exit_code != 0 and stderr_text.strip():
                output = f"{output}\n\nSTDERR:\n{stderr_text.strip()}"

            return CommandResult(
                success=exit_code == 0,
                output=output or "(no output)",
                exit_code=exit_code,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return CommandResult(
                success=False,
                output=f"Command timed out after {self.command_timeout:.0f} seconds.",
                exit_code=-1,
            )
        except FileNotFoundError:
            return CommandResult(
                success=False,
                output=(
                    f"Error: '{self.claude_executable}' CLI not found. "
                    "Is it installed and on PATH?"
                ),
                exit_code=-1,
            )

    async def _send_result(self, result: CommandResult) -> None:
        """Send result back to Telegram, splitting long output."""
        prefix = "" if result.success else f"Error (exit {result.exit_code}):\n\n"
        full_text = f"{prefix}{result.output}"
        chunks = split_message(full_text)
        for i, chunk in enumerate(chunks):
            # Send Claude output as plain text — it contains arbitrary formatting
            await self.client.send_message(chunk, parse_mode="")
            # Rate-limit when sending many chunks
            if i < len(chunks) - 1:
                await asyncio.sleep(0.5)

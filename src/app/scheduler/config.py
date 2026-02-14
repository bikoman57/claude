"""Scheduler configuration loaded from environment variables."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    """Configuration for scheduled runs."""

    project_dir: Path
    uv_executable: Path
    claude_executable: Path
    claude_timeout: int  # seconds for Claude CLI analysis
    logs_dir: Path
    research_timeout: int = 600  # seconds for research CLI analysis

    @classmethod
    def from_env(cls) -> SchedulerConfig:
        """Load scheduler configuration from environment variables."""
        load_dotenv()

        project_dir = Path(
            os.environ.get(
                "SCHEDULER_PROJECT_DIR",
                r"C:\Users\texcu\OneDrive\Documents\claude",
            ),
        )

        uv_path = os.environ.get(
            "UV_EXECUTABLE",
            r"C:\Users\texcu\.local\bin\uv.exe",
        )
        uv_executable = Path(uv_path)
        if not uv_executable.exists():
            msg = f"uv executable not found: {uv_executable}"
            raise FileNotFoundError(msg)

        claude_path = os.environ.get("CLAUDE_EXECUTABLE", "")
        claude_executable = Path(claude_path) if claude_path else _discover_claude_cli()

        claude_timeout = int(
            os.environ.get("CLAUDE_ANALYSIS_TIMEOUT", "3600"),
        )

        research_timeout = int(
            os.environ.get("RESEARCH_ANALYSIS_TIMEOUT", "600"),
        )

        logs_dir = project_dir / "data" / "logs"

        return cls(
            project_dir=project_dir,
            uv_executable=uv_executable,
            claude_executable=claude_executable,
            claude_timeout=claude_timeout,
            research_timeout=research_timeout,
            logs_dir=logs_dir,
        )


def _discover_claude_cli() -> Path:
    """Discover the Claude CLI executable.

    Search order: PATH -> common Windows install locations.
    """
    found = shutil.which("claude")
    if found:
        return Path(found)

    candidates = [
        Path.home() / ".claude" / "local" / "claude.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "claude" / "claude.exe",
        Path(r"C:\Program Files\Claude\claude.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    msg = (
        "Claude CLI not found. Set CLAUDE_EXECUTABLE environment variable "
        "or ensure 'claude' is on PATH."
    )
    raise FileNotFoundError(msg)

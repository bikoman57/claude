from __future__ import annotations

import re

_MARKDOWNV2_SPECIAL = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return _MARKDOWNV2_SPECIAL.sub(r"\\\1", text)


def bold(text: str) -> str:
    return f"*{escape_markdown(text)}*"


def code(text: str) -> str:
    return f"`{escape_markdown(text)}`"


def notification_message(title: str, body: str) -> str:
    """Format a structured notification message."""
    return f"{bold(title)}\n\n{escape_markdown(body)}"


def question_message(question: str, *, hint: str = "") -> str:
    """Format a question message for verification."""
    parts = [f"{bold('Question')}\n\n{escape_markdown(question)}"]
    if hint:
        parts.append(escape_markdown(hint))
    return "\n\n".join(parts)

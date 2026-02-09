from __future__ import annotations

from app.telegram.formatting import (
    bold,
    code,
    escape_markdown,
    notification_message,
    question_message,
)


def test_escape_markdown_special_chars() -> None:
    assert escape_markdown("hello.world") == r"hello\.world"
    assert escape_markdown("a-b") == r"a\-b"
    assert escape_markdown("(test)") == r"\(test\)"


def test_escape_markdown_no_special() -> None:
    assert escape_markdown("hello world") == "hello world"


def test_bold() -> None:
    result = bold("hello")
    assert result == "*hello*"


def test_bold_with_special() -> None:
    result = bold("hello.world")
    assert result == r"*hello\.world*"


def test_code() -> None:
    result = code("x = 1")
    assert result.startswith("`")
    assert result.endswith("`")


def test_notification_message_structure() -> None:
    result = notification_message("Build Done", "All tests passed.")
    assert "*Build Done*" in result
    assert r"All tests passed\." in result


def test_question_message_basic() -> None:
    result = question_message("Continue?")
    assert "*Question*" in result
    assert "Continue?" in result


def test_question_message_with_hint() -> None:
    result = question_message("Continue?", hint="Reply yes or no")
    assert "*Question*" in result
    assert "Continue?" in result
    assert "Reply yes or no" in result

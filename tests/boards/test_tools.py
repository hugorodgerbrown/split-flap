"""Tests for the boards' MCP tools."""

from typing import Any

import pytest

from apps.boards.services import display_for
from apps.mcp.tools import ToolError, get_board, list_boards, post_board_message

pytestmark = pytest.mark.django_db


def test_post_then_get_and_list(user: Any) -> None:
    """post_message writes to the board; get_board and list_boards read it back."""
    posted = post_board_message(user, {"text": "Hello from Claude"})
    assert posted["kind"] == "custom"
    assert get_board(user, {})["message"] == "Hello from Claude"
    listed = list_boards(user, {})
    assert listed["display"] == display_for(user).name
    assert [b["kind"] for b in listed["boards"]] == ["custom", "news", "weather", "travel"]


def test_post_to_another_board(user: Any) -> None:
    """The board argument picks the board."""
    post_board_message(user, {"text": "Rain later", "board": "weather"})
    assert get_board(user, {"board": "weather"})["message"] == "Rain later"


@pytest.mark.parametrize(
    "args", [{"text": "x", "board": "sports"}, {"text": 5}, {"text": "x" * 401}]
)
def test_post_errors_are_tool_errors(user: Any, args: dict[str, Any]) -> None:
    """Mistakes come back as ToolError so the model can correct them."""
    with pytest.raises(ToolError):
        post_board_message(user, args)


def test_get_unknown_board(user: Any) -> None:
    """Asking for a board that doesn't exist is a ToolError."""
    with pytest.raises(ToolError):
        get_board(user, {"board": "sports"})

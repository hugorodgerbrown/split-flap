"""Tests for the boards' MCP tools."""

from typing import Any

import pytest

from apps.boards.services import display_for
from apps.mcp.tools import TOOLS, ToolError, get_board, list_boards, post_board_message
from tests.factories import BoardFactory

pytestmark = pytest.mark.django_db


def test_post_then_get_and_list(user: Any) -> None:
    """post_message writes to the first board; get_board and list_boards read it back."""
    posted = post_board_message(user, {"text": "Hello from Claude"})
    assert posted["name"] == "Home"
    assert get_board(user, {})["message"] == "Hello from Claude"
    listed = list_boards(user, {})
    assert listed["display"] == display_for(user).name
    assert [b["name"] for b in listed["boards"]] == ["Home"]


def test_post_to_a_board_by_name(user: Any) -> None:
    """The board argument picks the board by name, in any case."""
    BoardFactory.create(display=display_for(user), name="Weather", position=1)
    post_board_message(user, {"text": "Rain later", "board": "weather"})
    assert get_board(user, {"board": "WEATHER"})["message"] == "Rain later"
    assert get_board(user, {})["message"] == ""


def test_boards_are_not_a_fixed_list() -> None:
    """The tools take any board name rather than an enum of kinds."""
    for name in ("post_message", "get_board"):
        board = TOOLS[name].input_schema["properties"]["board"]
        assert board["type"] == "string"
        assert "enum" not in board


@pytest.mark.parametrize(
    "args",
    [
        {"text": "x", "board": "Sports"},
        {"text": "x", "board": 3},
        {"text": 5},
        {"text": "x" * 401},
    ],
)
def test_post_errors_are_tool_errors(user: Any, args: dict[str, Any]) -> None:
    """Mistakes come back as ToolError so the model can correct them."""
    with pytest.raises(ToolError):
        post_board_message(user, args)


def test_get_unknown_board_names_the_boards(user: Any) -> None:
    """Asking for a board that doesn't exist says which boards there are."""
    with pytest.raises(ToolError, match="Home"):
        get_board(user, {"board": "Sports"})


def test_users_only_reach_their_own_boards(user: Any) -> None:
    """A board on someone else's display can't be read or written by name."""
    theirs = BoardFactory.create(name="Secret")
    with pytest.raises(ToolError):
        post_board_message(user, {"text": "hi", "board": "Secret"})
    theirs.refresh_from_db()
    assert theirs.message == ""

"""Tests for apps.boards.models and apps.boards.services."""

from typing import Any

import pytest

from apps.boards.models import MAX_MESSAGE_LENGTH, Board, BoardKind, Display
from apps.boards.services import BoardError, display_for, post_message
from tests.factories import BoardFactory, DisplayFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_display_for_makes_one_display_with_every_board(user: Any) -> None:
    """The first call makes the display and a board of each kind, in order."""
    display = display_for(user)
    assert [b.kind for b in display.boards.all()] == BoardKind.values
    assert display_for(user) == display
    assert Display.objects.count() == 1


def test_display_for_keeps_the_secret_out_of_the_log(
    user: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Making a display logs it without its uuid, the TV's secret."""
    with caplog.at_level("INFO", logger="apps.boards.services"):
        display = display_for(user)
    assert "Made display" in caplog.text
    assert str(display.uuid) not in caplog.text


def test_for_user_filters_by_owner() -> None:
    """for_user() returns only that user's displays and boards."""
    mine = BoardFactory.create()
    BoardFactory.create()
    assert list(Display.objects.for_user(mine.display.owner)) == [mine.display]
    assert list(Board.objects.for_user(mine.display.owner)) == [mine]


def test_post_message_sets_and_clears(user: Any) -> None:
    """A message is stored with its time; an empty one clears both."""
    display = display_for(user)
    board = post_message(display, "  Dinner at eight  ", BoardKind.NEWS)
    assert board.message == "Dinner at eight"
    assert board.posted_at is not None
    board = post_message(display, "", BoardKind.NEWS)
    assert board.message == ""
    assert board.posted_at is None


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("hello", "sports"),
        ("x" * (MAX_MESSAGE_LENGTH + 1), BoardKind.CUSTOM),
        ("\n".join(["row"] * 7), BoardKind.CUSTOM),
    ],
)
def test_post_message_refuses_bad_input(user: Any, text: str, kind: str) -> None:
    """An unknown board or a message that won't fit is a BoardError, not a save."""
    with pytest.raises(BoardError):
        post_message(display_for(user), text, kind)


def test_state_version_changes_with_content(user: Any) -> None:
    """The state's version is stable until a message changes."""
    display = display_for(user)
    before = display.state()["version"]
    assert Display.objects.get(pk=display.pk).state()["version"] == before
    post_message(display, "hi")
    assert Display.objects.get(pk=display.pk).state()["version"] != before


def test_to_string() -> None:
    """Displays read as their name; boards as kind on display."""
    board = BoardFactory.create(
        display=DisplayFactory.create(name="Kitchen", owner=UserFactory.create())
    )
    assert str(board.display) == "Kitchen"
    assert str(board) == "Custom on Kitchen"

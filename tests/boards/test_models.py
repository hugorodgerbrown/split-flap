"""Tests for apps.boards.models and apps.boards.services."""

from typing import Any

import pytest
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor

from apps.boards.models import (
    FIRST_BOARD_NAME,
    MAX_MESSAGE_LENGTH,
    MAX_NAME_LENGTH,
    Board,
    Display,
)
from apps.boards.services import (
    BoardError,
    add_board,
    check_name,
    delete_board,
    display_for,
    find_board,
    move_board,
    post_message,
    rename_board,
)
from tests.factories import BoardFactory, DisplayFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_display_for_makes_one_display_with_one_board(user: Any) -> None:
    """The first call makes the display and its Home board, and later calls find it."""
    display = display_for(user)
    assert [b.name for b in display.boards.all()] == [FIRST_BOARD_NAME]
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


def test_board_names_are_unique_per_display_ignoring_case() -> None:
    """A display can't have News and news; another display can have its own News."""
    board = BoardFactory.create(name="News")
    BoardFactory.create(name="News")
    with pytest.raises(IntegrityError):
        BoardFactory.create(display=board.display, name="news")


def test_find_board_by_name_ignoring_case(user: Any) -> None:
    """A board is found by its name in any case, and the first board by default."""
    display = display_for(user)
    weather = BoardFactory.create(display=display, name="Weather", position=1)
    assert find_board(display, "  WEATHER ") == weather
    assert find_board(display).name == FIRST_BOARD_NAME


def test_find_board_names_the_boards_when_it_fails(user: Any) -> None:
    """An unknown name is refused with the names there are, so a model can correct it."""
    display = display_for(user)
    with pytest.raises(BoardError, match="The boards are: Home"):
        find_board(display, "Sports")


def test_find_board_on_a_display_with_no_boards() -> None:
    """A display whose boards were all deleted says so."""
    with pytest.raises(BoardError, match="none yet"):
        find_board(DisplayFactory.create())


def test_post_message_sets_and_clears(user: Any) -> None:
    """A message is stored with its time; an empty one clears both."""
    display = display_for(user)
    BoardFactory.create(display=display, name="News", position=1)
    board = post_message(display, "  Dinner at eight  ", "news")
    assert board.name == "News"
    assert board.message == "Dinner at eight"
    assert board.posted_at is not None
    board = post_message(display, "", "News")
    assert board.message == ""
    assert board.posted_at is None


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("hello", "Sports"),
        ("x" * (MAX_MESSAGE_LENGTH + 1), None),
        ("\n".join(["row"] * 7), None),
    ],
)
def test_post_message_refuses_bad_input(user: Any, text: str, name: str | None) -> None:
    """An unknown board or a message that won't fit is a BoardError, not a save."""
    with pytest.raises(BoardError):
        post_message(display_for(user), text, name)
    assert display_for(user).boards.get().message == ""


@pytest.mark.parametrize(
    ("name", "error"),
    [
        ("   ", "Give the board a name"),
        ("x" * (MAX_NAME_LENGTH + 1), "under 40 characters"),
        ("HOME", "already a board called HOME"),
    ],
)
def test_check_name_refuses(user: Any, name: str, error: str) -> None:
    """A name is needed, short enough, and not another board's."""
    with pytest.raises(BoardError, match=error):
        check_name(display_for(user), name)


def test_check_name_tidies_spaces_and_lets_a_board_keep_its_name(user: Any) -> None:
    """Runs of spaces become one, and a board being renamed doesn't clash with itself."""
    display = display_for(user)
    assert check_name(display, "  Morning   news ") == "Morning news"
    assert check_name(display, "home", display.boards.get()) == "home"


def test_add_board_goes_on_the_end(user: Any) -> None:
    """A new board takes the next position, even after gaps."""
    display = display_for(user)
    BoardFactory.create(display=display, name="Far", position=7)
    assert add_board(display, "News").position == 8


def test_rename_board(user: Any) -> None:
    """Renaming saves the tidied name."""
    board = rename_board(display_for(user).boards.get(), " Kitchen ")
    board.refresh_from_db()
    assert board.name == "Kitchen"


def test_move_board_renumbers_ties(user: Any) -> None:
    """Boards sharing a position are numbered afresh, so a move always moves."""
    display = display_for(user)
    news = BoardFactory.create(display=display, name="News", position=0)
    move_board(news, -1)
    assert [(b.name, b.position) for b in Board.objects.filter(display=display)] == [
        ("News", 0),
        ("Home", 1),
    ]


def test_delete_board_keeps_the_last(user: Any) -> None:
    """The last board stays; any other goes."""
    display = display_for(user)
    news = BoardFactory.create(display=display, name="News", position=1)
    delete_board(news)
    with pytest.raises(BoardError, match="at least one board"):
        delete_board(display.boards.get())
    assert Board.objects.filter(display=display).count() == 1


def test_board_changes_lock_the_display(user: Any, monkeypatch: Any) -> None:
    """Adding, moving and deleting lock the display, so two at once can't break a limit."""
    display = display_for(user)
    locked = []
    real = Display.objects.select_for_update

    def spy(*args: Any, **kwargs: Any) -> Any:
        locked.append(True)
        return real(*args, **kwargs)

    monkeypatch.setattr(Display.objects, "select_for_update", spy)
    news = add_board(display, "News")
    move_board(news, -1)
    delete_board(news)
    assert len(locked) == 3


def test_state_version_changes_with_content(user: Any) -> None:
    """The state's version is stable until a message changes."""
    display = display_for(user)
    before = display.state()["version"]
    assert Display.objects.get(pk=display.pk).state()["version"] == before
    post_message(display, "hi")
    assert Display.objects.get(pk=display.pk).state()["version"] != before


def test_state_has_names_and_messages_only(user: Any) -> None:
    """The TV is told each board's name and message, and nothing about feeds."""
    board = display_for(user).boards.get()
    assert board.as_json() == {"name": FIRST_BOARD_NAME, "message": "", "posted_at": None}


def test_to_string() -> None:
    """Displays read as their name; boards as their name on the display."""
    board = BoardFactory.create(
        name="Weather", display=DisplayFactory.create(name="Kitchen", owner=UserFactory.create())
    )
    assert str(board.display) == "Kitchen"
    assert str(board) == "Weather on Kitchen"


@pytest.mark.django_db(transaction=True)
def test_migration_names_boards_after_their_kind() -> None:
    """Boards made before names keep their place, named after their old kind."""
    executor = MigrationExecutor(connection)
    executor.migrate([("boards", "0001_initial")])
    old_apps = executor.loader.project_state([("boards", "0001_initial")]).apps
    old_display = old_apps.get_model("boards", "Display")
    old_board = old_apps.get_model("boards", "Board")
    display = old_display.objects.create(owner_id=UserFactory.create().pk)
    for position, kind in enumerate(["custom", "news", "weather", "travel"]):
        old_board.objects.create(display=display, kind=kind, position=position)
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
    names = Board.objects.filter(display_id=display.pk).values_list("name", flat=True)
    assert list(names) == ["Custom", "News", "Weather", "Travel"]

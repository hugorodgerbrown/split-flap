"""What can happen to a display, called from views and MCP tools alike."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.boards.layout import COLS, ROWS, rows_needed
from apps.boards.models import (
    FIRST_BOARD_NAME,
    MAX_BOARDS,
    MAX_MESSAGE_LENGTH,
    MAX_NAME_LENGTH,
    MAX_SOUND_DELAY_MS,
    SOUND_DELAY_STEP_MS,
    SOUND_DELAYS_MS,
    Board,
    Display,
)

logger = logging.getLogger(__name__)


class BoardError(ValueError):
    """A message or board name that can't be used, worded for the person or model."""


def display_for(user: AbstractBaseUser) -> Display:
    """Return ``user``'s display, making it and its first board on first use."""
    display = Display.objects.for_user(user).prefetch_related("boards").first()
    if display:
        return display
    with transaction.atomic():
        # Lock the owner so two first visits at once make one display, not two.
        get_user_model().objects.select_for_update().filter(pk=user.pk).first()
        display = Display.objects.for_user(user).first()
        if display is None:
            display = Display.objects.create(owner_id=user.pk)
            Board.objects.create(display=display, name=FIRST_BOARD_NAME)
            # The uuid is the TV's secret, so it stays out of the logs.
            logger.info("Made display %s", display.pk)
    return Display.objects.prefetch_related("boards").get(pk=display.pk)


def check_fits(text: str) -> None:
    """Raise BoardError if ``text`` won't fit on the board once it's wrapped."""
    if len(text) > MAX_MESSAGE_LENGTH:
        raise BoardError(
            f"That message is too long: keep it under {MAX_MESSAGE_LENGTH} characters."
        )
    rows = rows_needed(text)
    if rows > ROWS:
        raise BoardError(
            f"That message needs {rows} rows but the board has {ROWS} rows of {COLS} tiles: "
            "shorten it so nothing is cut off."
        )


def find_board(display: Display, name: str | None = None) -> Board:
    """Return the board on ``display`` called ``name``, ignoring case, or its first board.

    Raises:
        BoardError: if there's no such board, naming the ones there are.
    """
    boards = display.boards.all()
    board = boards.named(name).first() if name else boards.first()
    if board is None:
        names = ", ".join(b.name for b in boards) or "none yet"
        raise BoardError(f"There's no board called {name!r}. The boards are: {names}.")
    return board


def post_message(display: Display, text: str, name: str | None = None) -> Board:
    """Put ``text`` on the board called ``name`` (or the first); an empty text clears it."""
    text = text.strip()
    check_fits(text)
    board = find_board(display, name)
    board.message = text
    board.posted_at = timezone.now() if text else None
    board.save(update_fields=["message", "posted_at", "updated_at"])
    return board


def check_name(display: Display, name: str) -> str:
    """Return ``name`` tidied, or raise BoardError if ``display`` can't take it.

    A name is unique on its display, ignoring case.
    """
    name = " ".join(name.split())
    if not name:
        raise BoardError("Give the board a name.")
    if len(name) > MAX_NAME_LENGTH:
        raise BoardError(f"Keep the name under {MAX_NAME_LENGTH} characters.")
    if display.boards.named(name).exists():
        raise BoardError(f"There's already a board called {name}.")
    return name


def _boards_locked(display_id: int) -> list[Board]:
    """Lock the display and return its boards, read afresh, inside the caller's transaction.

    Changes that count or renumber a display's boards take this lock first,
    so two at once (two tabs) can't both pass a check meant for one.
    """
    Display.objects.select_for_update().filter(pk=display_id).first()
    return list(Board.objects.filter(display_id=display_id))


def add_board(display: Display, name: str) -> Board:
    """Add a board called ``name`` to the end of ``display``'s boards."""
    name = check_name(display, name)
    with transaction.atomic():
        boards = _boards_locked(display.pk)
        if len(boards) >= MAX_BOARDS:
            raise BoardError(
                f"A display holds up to {MAX_BOARDS} boards: delete one to add another."
            )
        position = max((b.position for b in boards), default=-1) + 1
        return Board.objects.create(display=display, name=name, position=position)


def set_sound(display: Display, on: bool) -> Display:
    """Turn ``display``'s flap sound on or off; the TV follows at its next poll."""
    display.sound = on
    display.save(update_fields=["sound", "updated_at"])
    return display


def set_sound_delay(display: Display, delay_ms: int) -> Display:
    """Hold ``display``'s flaps back by ``delay_ms`` so the clack lands with them.

    Raises:
        ValueError: ``delay_ms`` isn't a step of the Sound timing setting.
    """
    if delay_ms not in SOUND_DELAYS_MS:
        raise ValueError(
            f"Sound timing is a step of {SOUND_DELAY_STEP_MS} ms up to {MAX_SOUND_DELAY_MS} ms."
        )
    display.sound_delay_ms = delay_ms
    display.save(update_fields=["sound_delay_ms", "updated_at"])
    return display


def replay(display: Display) -> Display:
    """Have ``display``'s TV flip its board again at its next poll."""
    Display.objects.filter(pk=display.pk).update(
        replays=F("replays") + 1, updated_at=timezone.now()
    )
    display.refresh_from_db(fields=["replays", "updated_at"])
    return display


def delete_board(board: Board) -> None:
    """Delete ``board``, unless it's its display's last one."""
    with transaction.atomic():
        if len(_boards_locked(board.display_id)) <= 1:
            raise BoardError("A display needs at least one board, so this one stays.")
        board.delete()

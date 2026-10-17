"""What can happen to a display, called from views and MCP tools alike."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from apps.boards.layout import COLS, ROWS, rows_needed
from apps.boards.models import FIRST_BOARD_NAME, MAX_MESSAGE_LENGTH, Board, Display

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

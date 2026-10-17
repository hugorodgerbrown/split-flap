"""What can happen to a display, called from views and MCP tools alike."""

from __future__ import annotations

import logging

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from apps.boards.models import MAX_MESSAGE_LENGTH, Board, BoardKind, Display

logger = logging.getLogger(__name__)


class BoardError(ValueError):
    """A message or board name that can't be used, worded for the person or model."""


def display_for(user: AbstractBaseUser) -> Display:
    """Return ``user``'s display, making it and its boards on first use."""
    display = Display.objects.for_user(user).prefetch_related("boards").first()
    if display:
        return display
    with transaction.atomic():
        display = Display.objects.create(owner_id=user.pk)
        Board.objects.bulk_create(
            Board(display=display, kind=kind, position=position)
            for position, kind in enumerate(BoardKind.values)
        )
    logger.info("Made display %s", display.uuid)
    return Display.objects.prefetch_related("boards").get(pk=display.pk)


def post_message(display: Display, text: str, kind: str = BoardKind.CUSTOM) -> Board:
    """Put ``text`` on the ``kind`` board of ``display``; an empty text clears it."""
    if kind not in BoardKind.values:
        raise BoardError(f"There's no {kind!r} board. Use one of: {', '.join(BoardKind.values)}.")
    text = text.strip()
    if len(text) > MAX_MESSAGE_LENGTH:
        raise BoardError(
            f"That message is too long: keep it under {MAX_MESSAGE_LENGTH} characters."
        )
    board = display.boards.get(kind=kind)
    board.message = text
    board.posted_at = timezone.now() if text else None
    board.save(update_fields=["message", "posted_at", "updated_at"])
    return board

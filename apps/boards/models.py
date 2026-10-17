"""Displays and boards.

A Display is what one TV shows. Its uuid is the secret in the TV's address
(``/d/<uuid>/``), so the TV needs no sign-in. Each display holds named
Boards, and each board shows only the message it was last given: there are
no feeds here. Anything live (news, weather) is pushed to a board from
outside, by a person or a Claude Routine.
"""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import BaseModel

# Longest message a board takes: six rows of 22 tiles, with room for the
# {r}-style colour codes and line breaks that don't take a tile each.
MAX_MESSAGE_LENGTH = 400


# Longest board name; short enough to read on the TV's engraved label.
MAX_NAME_LENGTH = 40

# Most boards one display holds: the TV picks the first nine by number key,
# and a cycle much longer than this is never seen through.
MAX_BOARDS = 12

# The board a new display starts with.
FIRST_BOARD_NAME = "Home"

# How far the display page's Sound timing setting can hold the flaps back, and
# its step: enough for a soundbar or receiver, in steps an ear can tell apart.
MAX_SOUND_DELAY_MS = 500
SOUND_DELAY_STEP_MS = 50
SOUND_DELAYS_MS = tuple(range(0, MAX_SOUND_DELAY_MS + 1, SOUND_DELAY_STEP_MS))


class DisplayQuerySet(models.QuerySet["Display"]):
    """Queries over displays."""

    def for_user(self, user: AbstractBaseUser) -> DisplayQuerySet:
        """Return the displays ``user`` owns."""
        return self.filter(owner=user)


class Display(BaseModel):
    """One split-flap display, as a TV shows it."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=60, default="Living room")
    # Whether the TV plays the flap sound. Browsers start it at the TV's first
    # tap or key press, so "on" means "as soon as the browser allows".
    sound = models.BooleanField(default=False)
    # How long the TV holds the flaps back so each clack is heard with its flap,
    # on top of the delay the browser reports: a soundbar's delay is unseen.
    sound_delay_ms = models.PositiveSmallIntegerField(default=0)
    # Bumped by the display page's Replay button; the TV flips its board again
    # whenever it changes.
    replays = models.PositiveIntegerField(default=0)

    objects = DisplayQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        """Model metadata."""

        ordering = ["created_at", "id"]

    def to_string(self) -> str:
        """Return the display's name."""
        return self.name

    def state(self) -> dict[str, object]:
        """Return what the TV needs to draw every board, and a version for caching."""
        boards = [board.as_json() for board in self.boards.all()]
        settings_ = (self.sound, self.sound_delay_ms, self.replays)
        version = hashlib.sha256(repr((settings_, boards)).encode()).hexdigest()[:16]
        return {
            "name": self.name,
            "sound": self.sound,
            "sound_delay_ms": self.sound_delay_ms,
            "replays": self.replays,
            "boards": boards,
            "version": version,
        }


class BoardQuerySet(models.QuerySet["Board"]):
    """Queries over boards."""

    def for_user(self, user: AbstractBaseUser) -> BoardQuerySet:
        """Return the boards on displays ``user`` owns."""
        return self.filter(display__owner=user)

    def named(self, name: str) -> BoardQuerySet:
        """Return the boards called ``name``, ignoring case and outer spaces."""
        return self.filter(name__iexact=name.strip())


class Board(BaseModel):
    """One board on a display: a name and the message it was last given.

    An empty message means the TV shows the board's name.
    """

    display = models.ForeignKey(Display, on_delete=models.CASCADE, related_name="boards")
    name = models.CharField(max_length=MAX_NAME_LENGTH)
    position = models.PositiveSmallIntegerField(default=0)
    message = models.TextField(max_length=MAX_MESSAGE_LENGTH, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    objects = BoardQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        """Model metadata."""

        ordering = ["display", "position", "id"]
        constraints = [
            models.UniqueConstraint("display", Lower("name"), name="one_board_per_name"),
        ]

    def to_string(self) -> str:
        """Return the board's name and display."""
        return f"{self.name} on {self.display}"

    def as_json(self) -> dict[str, object]:
        """Return the board as the TV and the MCP tools see it."""
        return {
            "name": self.name,
            "message": self.message,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
        }

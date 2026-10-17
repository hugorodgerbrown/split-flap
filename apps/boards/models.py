"""Displays and boards.

A Display is what one TV shows. Its uuid is the secret in the TV's address
(``/d/<uuid>/``), so the TV needs no sign-in. Each display holds one Board
per kind, and each board holds the message the TV shows on it.
"""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from apps.core.models import BaseModel

# Longest message a board takes: six rows of 22 tiles, with room for the
# {r}-style colour codes and line breaks that don't take a tile each.
MAX_MESSAGE_LENGTH = 400


class BoardKind(models.TextChoices):
    """The boards every display has, in the order the TV shows them."""

    CUSTOM = "custom", "Custom"
    NEWS = "news", "News"
    WEATHER = "weather", "Weather"
    TRAVEL = "travel", "Travel"


class DisplayQuerySet(models.QuerySet["Display"]):
    """Queries over displays."""

    def for_user(self, user: AbstractBaseUser) -> DisplayQuerySet:
        """Return the displays ``user`` owns."""
        return self.filter(owner=user)


class Display(BaseModel):
    """One split-flap display, as a TV shows it."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=60, default="Living room")

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
        version = hashlib.sha256(repr(boards).encode()).hexdigest()[:16]
        return {"name": self.name, "boards": boards, "version": version}


class BoardQuerySet(models.QuerySet["Board"]):
    """Queries over boards."""

    def for_user(self, user: AbstractBaseUser) -> BoardQuerySet:
        """Return the boards on displays ``user`` owns."""
        return self.filter(display__owner=user)


class Board(BaseModel):
    """One board on a display: a kind and the message it shows.

    An empty message means the TV draws the board's own content (a greeting
    on Custom, sample content on the others until their feeds arrive).
    """

    display = models.ForeignKey(Display, on_delete=models.CASCADE, related_name="boards")
    kind = models.CharField(max_length=16, choices=BoardKind.choices)
    position = models.PositiveSmallIntegerField(default=0)
    message = models.TextField(max_length=MAX_MESSAGE_LENGTH, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    objects = BoardQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        """Model metadata."""

        ordering = ["display", "position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["display", "kind"], name="one_board_per_kind"),
        ]

    def to_string(self) -> str:
        """Return the board's name and display."""
        return f"{self.get_kind_display()} on {self.display}"

    def as_json(self) -> dict[str, object]:
        """Return the board as the TV and the MCP tools see it."""
        return {
            "kind": self.kind,
            "name": self.get_kind_display(),
            "message": self.message,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
        }

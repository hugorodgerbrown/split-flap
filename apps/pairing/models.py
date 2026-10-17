"""TV pairings: a short code a TV shows, claimed by the display's owner.

A TV app starts a pairing and shows its code; the owner types it on their
phone; the TV's next poll is answered with the display's link, once. Only
hashes of the code and the poll token are stored, so a copy of the
database links no TV to anything.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.boards.models import Display
from apps.core.models import BaseModel


class TVPairingQuerySet(models.QuerySet["TVPairing"]):
    """Queries over pairings."""

    def live(self) -> TVPairingQuerySet:
        """Return pairings still waiting for their code: unclaimed and unexpired."""
        return self.filter(claimed_at__isnull=True, expires_at__gt=timezone.now())

    def expired(self) -> TVPairingQuerySet:
        """Return pairings past their expiry, claimed or not: safe to delete."""
        return self.filter(expires_at__lte=timezone.now())


class TVPairing(BaseModel):
    """One TV asking to be linked to a display.

    ``claimed_at`` is when the owner entered the code (and ``display`` is
    theirs); ``delivered_at`` is when the TV collected the link, after which
    the pairing answers nothing more.
    """

    token_hash = models.CharField(max_length=64, unique=True)
    code_hash = models.CharField(max_length=64, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    display = models.ForeignKey(Display, on_delete=models.CASCADE, null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    objects = TVPairingQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        """Model metadata."""

        ordering = ["-created_at", "-id"]

    def is_expired(self) -> bool:
        """Return True once the pairing is past its expiry."""
        return self.expires_at <= timezone.now()

    def to_string(self) -> str:
        """Return how far the pairing got."""
        if self.delivered_at:
            state = "delivered"
        elif self.claimed_at:
            state = "claimed"
        elif self.is_expired():
            state = "expired"
        else:
            state = "waiting"
        return f"TV pairing ({state})"

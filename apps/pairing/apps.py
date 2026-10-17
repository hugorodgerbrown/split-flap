"""App config for apps.pairing."""

from django.apps import AppConfig


class PairingConfig(AppConfig):
    """Linking a TV app to a display with a short code instead of its link."""

    name = "apps.pairing"
    label = "pairing"

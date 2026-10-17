"""Forms for a display's boards: a board's message and a new board's name, and its sound."""

from typing import Any

from django import forms

from apps.boards.models import (
    MAX_MESSAGE_LENGTH,
    MAX_NAME_LENGTH,
    SOUND_DELAYS_MS,
    Display,
)
from apps.boards.services import BoardError, check_fits, check_name


class MessageForm(forms.Form):
    """A board's message; an empty message clears the board."""

    text = forms.CharField(
        label="Message",
        max_length=MAX_MESSAGE_LENGTH,
        required=False,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 6, "aria-describedby": "message-counts"}),
    )

    def clean_text(self) -> str:
        """Refuse a message that would lose its end on the board."""
        text: str = self.cleaned_data["text"]
        try:
            check_fits(text)
        except BoardError as error:
            raise forms.ValidationError(str(error)) from error
        return text


class BoardNameForm(forms.Form):
    """A name for a new board on ``display``."""

    name = forms.CharField(
        label="Name",
        max_length=MAX_NAME_LENGTH,
        widget=forms.TextInput(
            attrs={"placeholder": "For example, Weather", "autocomplete": "off"}
        ),
    )

    def __init__(self, display: Display, *args: Any, **kwargs: Any) -> None:
        """Check names against ``display``'s boards."""
        super().__init__(*args, **kwargs)
        self.display = display

    def clean_name(self) -> str:
        """Refuse a name another board on the display has."""
        try:
            return check_name(self.display, self.cleaned_data["name"])
        except BoardError as error:
            raise forms.ValidationError(str(error)) from error


class SoundForm(forms.Form):
    """Whether the display plays the flap sound."""

    sound = forms.ChoiceField(choices=[("on", "On"), ("off", "Off")])

    def on(self) -> bool:
        """Return whether the sound was turned on."""
        return bool(self.cleaned_data["sound"] == "on")


class SoundDelayForm(forms.Form):
    """How long the display holds its flaps back for the sound (Sound timing)."""

    sound_delay_ms = forms.TypedChoiceField(
        coerce=int, choices=[(str(ms), f"{ms} ms") for ms in SOUND_DELAYS_MS]
    )

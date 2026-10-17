"""Forms for a display's boards: a board's message, its name, and its place."""

from typing import Any

from django import forms

from apps.boards.models import MAX_MESSAGE_LENGTH, MAX_NAME_LENGTH, Board, Display
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
    """A name for a new board on ``display``, or a new name for ``board``."""

    name = forms.CharField(
        label="Name",
        max_length=MAX_NAME_LENGTH,
        widget=forms.TextInput(
            attrs={"placeholder": "For example, Weather", "autocomplete": "off"}
        ),
    )

    def __init__(
        self, display: Display, *args: Any, board: Board | None = None, **kwargs: Any
    ) -> None:
        """Check names against ``display``'s boards, other than ``board`` itself."""
        super().__init__(*args, **kwargs)
        self.display = display
        self.board = board

    def clean_name(self) -> str:
        """Refuse a name another board on the display has."""
        try:
            return check_name(self.display, self.cleaned_data["name"], self.board)
        except BoardError as error:
            raise forms.ValidationError(str(error)) from error


class MoveForm(forms.Form):
    """Which way to move a board in its display's order."""

    direction = forms.ChoiceField(choices=[("up", "Up"), ("down", "Down")])

    def step(self) -> int:
        """Return the move as a step along the order."""
        return -1 if self.cleaned_data["direction"] == "up" else 1

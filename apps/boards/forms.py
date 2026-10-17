"""Forms for posting to a board from the app."""

from typing import Any, cast

from django import forms

from apps.boards.models import MAX_MESSAGE_LENGTH, Display
from apps.boards.services import BoardError, check_fits


class PostMessageForm(forms.Form):
    """A message for one of a display's boards; an empty message clears the board."""

    board = forms.ChoiceField()
    text = forms.CharField(
        max_length=MAX_MESSAGE_LENGTH,
        required=False,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3, "aria-describedby": "text-help"}),
    )

    def __init__(self, display: Display, *args: Any, **kwargs: Any) -> None:
        """Offer the boards on ``display``, by name."""
        super().__init__(*args, **kwargs)
        board = cast(forms.ChoiceField, self.fields["board"])
        board.choices = [(b.name, b.name) for b in display.boards.all()]

    def clean_text(self) -> str:
        """Refuse a message that would lose its end on the board."""
        text: str = self.cleaned_data["text"]
        try:
            check_fits(text)
        except BoardError as error:
            raise forms.ValidationError(str(error)) from error
        return text

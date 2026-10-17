"""Forms for posting to a board from the app."""

from django import forms

from apps.boards.models import MAX_MESSAGE_LENGTH, BoardKind
from apps.boards.services import BoardError, check_fits


class PostMessageForm(forms.Form):
    """A message for one board; an empty message puts the board's own content back."""

    kind = forms.ChoiceField(choices=BoardKind.choices, initial=BoardKind.CUSTOM)
    text = forms.CharField(
        max_length=MAX_MESSAGE_LENGTH,
        required=False,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3, "aria-describedby": "text-help"}),
    )

    def clean_text(self) -> str:
        """Refuse a message that would lose its end on the board."""
        text: str = self.cleaned_data["text"]
        try:
            check_fits(text)
        except BoardError as error:
            raise forms.ValidationError(str(error)) from error
        return text

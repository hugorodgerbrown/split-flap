"""Forms for posting to a board from the app."""

from django import forms

from apps.boards.models import MAX_MESSAGE_LENGTH, BoardKind


class PostMessageForm(forms.Form):
    """A message for one board; an empty message puts the board's own content back."""

    kind = forms.ChoiceField(choices=BoardKind.choices, initial=BoardKind.CUSTOM)
    text = forms.CharField(
        max_length=MAX_MESSAGE_LENGTH,
        required=False,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3, "aria-describedby": "text-help"}),
    )

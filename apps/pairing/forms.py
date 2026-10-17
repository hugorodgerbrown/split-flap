"""The form the display's owner types a TV's code into."""

from django import forms

from apps.pairing.services import CODE_LENGTH, normalise_code


class PairForm(forms.Form):
    """The code a TV shows, with or without its dash."""

    code = forms.CharField(max_length=20, strip=True)

    def clean_code(self) -> str:
        """Return the bare code, or say what a code looks like."""
        code = normalise_code(self.cleaned_data["code"])
        if len(code) != CODE_LENGTH:
            raise forms.ValidationError(
                f"A code is {CODE_LENGTH} letters and numbers, like K7Q-4MD."
            )
        return code

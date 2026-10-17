"""board.css loads beside app.css on the front page and the display's pages: no collisions."""

from pathlib import Path

from django.conf import settings

from apps.design import stylesheet

CSS = Path(settings.BASE_DIR) / "static" / "css"


def test_board_css_and_app_css_share_no_class() -> None:
    """A class in both lets one stylesheet's rules leak onto the other's elements."""
    board = stylesheet.class_names((CSS / "board.css").read_text())
    app = stylesheet.class_names((CSS / "app.css").read_text())
    assert not board & app, sorted(board & app)

"""The app is called Riffle everywhere a person sees its name.

"Split-flap" stays as the word for the kind of display, but the old name,
Split-Flap, is gone from every page, the manifest, the MCP server and the TV
app. This guards against it creeping back in a copied string.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from apps.pwa import conf

BASE = Path(settings.BASE_DIR)
OLD_NAME = re.compile(r"Split-Flap")
SEEN = [
    *BASE.glob("templates/**/*.html"),
    *BASE.glob("apps/**/templates/**/*.html"),
    *BASE.glob("apps/**/*.py"),
    *BASE.glob("static/js/*.js"),
    BASE / "android-tv/app/src/main/res/values/strings.xml",
]


def test_the_name_is_riffle() -> None:
    """The one place the name is set says Riffle."""
    assert conf.APP_NAME == "Riffle"


@pytest.mark.parametrize("path", SEEN, ids=lambda p: str(p.relative_to(BASE)))
def test_no_old_name(path: Path) -> None:
    """No page, script, tool or TV string calls the app Split-Flap."""
    assert not OLD_NAME.search(path.read_text()), path


@pytest.mark.django_db
def test_pages_and_manifest_say_riffle(client: Client) -> None:
    """The front page's title, header and link tags and the manifest name the app Riffle."""
    home = client.get(reverse("public:home")).content.decode()
    assert "<title>Riffle: a split-flap display for any screen</title>" in home
    assert '<meta property="og:site_name" content="Riffle">' in home
    assert 'src="/static/img/wordmark.png" alt="Riffle"' in home
    assert 'href="/static/icons/favicon-32.png"' in home
    manifest = client.get(reverse("pwa:manifest")).json()
    assert manifest["name"] == "Riffle"

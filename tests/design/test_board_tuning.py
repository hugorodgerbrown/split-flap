"""The board tuning page: staff only, with a slider for every tunable number."""

import json
import re
from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse

from apps.design.views import TUNING_SLIDERS, tuning_boards
from apps.public.board import DEMO_BOARDS
from tests.factories import UserFactory

URL = reverse("design:board")
FLAPMOTION_JS = (
    Path(__file__).resolve().parents[2] / "static" / "js" / "flapmotion.js"
).read_text()


@pytest.fixture
def staff(client: Client, db: None) -> Client:
    """The test client, signed in as staff."""
    client.force_login(UserFactory.create(is_staff=True))
    return client


@pytest.mark.django_db
def test_signed_out_is_sent_to_sign_in(client: Client) -> None:
    """Signed-out visitors go to sign in, like every page under /app/."""
    assert client.get(URL).status_code == 302


def test_people_who_arent_staff_get_a_404(signed_in: Client) -> None:
    """To anyone else the page isn't there."""
    assert signed_in.get(URL).status_code == 404


def test_staff_get_a_slider_for_each_number(staff: Client) -> None:
    """Every slider is on the page, named for its number in TUNING."""
    response = staff.get(URL)
    assert response.status_code == 200
    page = response.content.decode()
    for key, *_rest in TUNING_SLIDERS:
        assert f'type="range" name="{key}"' in page


def test_every_number_in_the_code_has_a_slider() -> None:
    """The sliders and flapmotion.js's DEFAULTS name the same numbers."""
    defaults = re.search(r"DEFAULTS = Object\.freeze\(\{(.*?)\}\);", FLAPMOTION_JS, re.S)
    assert defaults
    keys = re.findall(r"^\s*(\w+):", defaults.group(1), re.M)
    assert keys == [key for key, *_rest in TUNING_SLIDERS]


def test_the_boards_are_blank_and_the_front_pages(staff: Client) -> None:
    """It changes between a blank board and each of the front page's demo boards."""
    boards = tuning_boards()
    assert [b["name"] for b in boards] == ["Blank"] + [name for name, _rows in DEMO_BOARDS]
    page = staff.get(URL).content.decode()
    assert json.dumps(boards).replace('"', "&quot;")[:40] in page


def test_the_design_page_links_to_it(staff: Client) -> None:
    """Staff find it from the design page."""
    assert URL in staff.get(reverse("design:index")).content.decode()

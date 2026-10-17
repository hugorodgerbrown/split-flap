"""Tests for apps.boards.views: the TV's page and state, and the signed-in page."""

import uuid
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from apps.boards.services import display_for, post_message
from tests.factories import BoardFactory

pytestmark = pytest.mark.django_db


def test_tv_page_needs_no_sign_in(client: Client, user: Any) -> None:
    """The TV opens the board by its secret address alone."""
    display = display_for(user)
    response = client.get(reverse("tv:board", args=[display.uuid]))
    assert response.status_code == 200
    assert reverse("tv:state", args=[display.uuid]).encode() in response.content


def test_unknown_display_is_404(client: Client) -> None:
    """A made-up uuid shows nothing."""
    assert client.get(reverse("tv:board", args=[uuid.uuid4()])).status_code == 404
    assert client.get(reverse("tv:state", args=[uuid.uuid4()])).status_code == 404


def test_state_is_json_with_an_etag(client: Client, user: Any) -> None:
    """The state lists every board and answers 304 until something changes."""
    display = display_for(user)
    url = reverse("tv:state", args=[display.uuid])
    first = client.get(url)
    assert first.status_code == 200
    assert [b["name"] for b in first.json()["boards"]] == ["Home"]
    assert first["Cache-Control"] == "no-cache"
    assert client.get(url, headers={"If-None-Match": first["ETag"]}).status_code == 304
    post_message(display, "hello")
    changed = client.get(url, headers={"If-None-Match": first["ETag"]})
    assert changed.status_code == 200
    assert changed.json()["boards"][0]["message"] == "hello"


def test_state_query_count_is_small(
    client: Client, user: Any, django_assert_max_num_queries: Any
) -> None:
    """Polling costs two queries: the display and its boards."""
    display = display_for(user)
    with django_assert_max_num_queries(2):
        client.get(reverse("tv:state", args=[display.uuid]))


def test_manage_needs_sign_in(client: Client) -> None:
    """Signed-out visitors are sent to sign in."""
    assert client.get(reverse("boards:manage")).status_code == 302


def test_manage_shows_the_tv_link(signed_in: Client, user: Any) -> None:
    """The signed-in page shows the TV's address."""
    response = signed_in.get(reverse("boards:manage"))
    assert response.status_code == 200
    assert str(display_for(user).uuid).encode() in response.content


def test_post_puts_the_message_on_the_board(signed_in: Client, user: Any) -> None:
    """A form post sets the board's message and goes back to the page."""
    BoardFactory.create(display=display_for(user), name="Weather", position=1)
    response = signed_in.post(reverse("boards:post"), {"board": "Weather", "text": "Sunny"})
    assert response.status_code == 302
    assert display_for(user).boards.get(name="Weather").message == "Sunny"


def test_post_refuses_an_unknown_board(signed_in: Client) -> None:
    """An invalid form redraws the page with its errors."""
    response = signed_in.post(reverse("boards:post"), {"board": "Sports", "text": "Goal"})
    assert response.status_code == 400


def test_post_refuses_a_message_that_wont_fit(signed_in: Client, user: Any) -> None:
    """A message longer than six rows is refused with the reason, not cut off."""
    text = "\n".join(["row"] * 7)
    response = signed_in.post(reverse("boards:post"), {"board": "Home", "text": text})
    assert response.status_code == 400
    assert "needs 7 rows" in response.content.decode()
    assert display_for(user).boards.get(name="Home").message == ""

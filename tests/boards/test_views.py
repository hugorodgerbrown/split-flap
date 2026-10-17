"""Tests for apps.boards.views: the TV's page and state, and the signed-in pages."""

import uuid
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from apps.boards.models import MAX_BOARDS
from apps.boards.services import display_for, post_message, replay, set_sound, set_sound_delay
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


@pytest.mark.parametrize(
    ("name", "method"),
    [
        ("boards:board", "get"),
        ("boards:message", "post"),
        ("boards:rename", "post"),
        ("boards:move", "post"),
        ("boards:delete", "get"),
        ("boards:delete", "post"),
    ],
)
def test_board_pages_need_sign_in(client: Client, user: Any, name: str, method: str) -> None:
    """Signed-out visitors are sent to sign in, and nothing changes."""
    board = display_for(user).boards.get()
    response = getattr(client, method)(reverse(name, args=[board.uuid]), {"text": "x"})
    assert response.status_code == 302
    assert "/signin/" in response["Location"]
    assert display_for(user).boards.get().message == ""


@pytest.mark.parametrize(
    ("name", "method"),
    [
        ("boards:board", "get"),
        ("boards:message", "post"),
        ("boards:rename", "post"),
        ("boards:move", "post"),
        ("boards:delete", "get"),
        ("boards:delete", "post"),
    ],
)
def test_someone_elses_board_is_404(signed_in: Client, name: str, method: str) -> None:
    """A board on another person's display can't be seen or changed."""
    other = BoardFactory.create(message="Theirs")
    BoardFactory.create(display=other.display)
    response = getattr(signed_in, method)(reverse(name, args=[other.uuid]), {"text": "Mine"})
    assert response.status_code == 404
    other.refresh_from_db()
    assert other.message == "Theirs"


def test_manage_needs_sign_in(client: Client) -> None:
    """Signed-out visitors are sent to sign in."""
    assert client.get(reverse("boards:manage")).status_code == 302
    assert client.post(reverse("boards:add"), {"name": "News"}).status_code == 302


def test_manage_shows_the_links_preview_and_boards(signed_in: Client, user: Any) -> None:
    """The display page has the display's link, the MCP address, and each board in order."""
    display = display_for(user)
    post_message(display, "Hello :sun:")
    BoardFactory.create(display=display, name="Weather", position=1)
    response = signed_in.get(reverse("boards:manage"))
    content = response.content.decode()
    assert response.status_code == 200
    assert f"/d/{display.uuid}/" in content
    assert "/mcp" in content
    assert content.index("Home") < content.index("Weather")
    assert 'aria-label="Home: Hello :sun:"' in content
    assert "pictograms.svg#sun" in content
    assert 'aria-label="Move Home up" disabled' in content
    assert 'aria-label="Move Weather down" disabled' in content


def test_manage_tells_the_preview_when_its_board_was_posted(
    signed_in: Client, user: Any, client: Client
) -> None:
    """The live preview compares this with the TV's state, so it redraws only on a newer post."""
    display = display_for(user)
    post_message(display, "Hello")
    posted_at = client.get(reverse("tv:state", args=[display.uuid])).json()["boards"][0][
        "posted_at"
    ]
    page = signed_in.get(reverse("boards:manage")).content.decode()
    assert f'data-posted-at="{posted_at}"' in page


def test_manage_previews_the_board_asked_for(signed_in: Client, user: Any) -> None:
    """``?board=`` picks which board the preview draws; an unknown one draws the first."""
    weather = BoardFactory.create(display=display_for(user), name="Weather", position=1)
    picked = signed_in.get(reverse("boards:manage"), {"board": str(weather.uuid)})
    assert 'aria-label="Weather: Weather"' in picked.content.decode()
    unknown = signed_in.get(reverse("boards:manage"), {"board": "nope"})
    assert 'aria-label="Home: Home"' in unknown.content.decode()


def test_manage_query_count_is_small(
    signed_in: Client, user: Any, django_assert_max_num_queries: Any
) -> None:
    """The display page costs the same however many boards there are."""
    display = display_for(user)
    for position in range(1, 6):
        BoardFactory.create(display=display, position=position)
    with django_assert_max_num_queries(8):
        signed_in.get(reverse("boards:manage"))


def test_add_board_opens_its_page(signed_in: Client, user: Any) -> None:
    """A new board goes on the end of the display, and you land on its page."""
    response = signed_in.post(reverse("boards:add"), {"name": "  News  "})
    board = display_for(user).boards.get(name="News")
    assert response.status_code == 302
    assert response["Location"] == reverse("boards:board", args=[board.uuid])
    assert [b.name for b in display_for(user).boards.all()] == ["Home", "News"]


@pytest.mark.parametrize(
    ("name", "error"),
    [("home", "already a board called home"), ("", "This field is required")],
)
def test_add_board_refuses_a_bad_name(signed_in: Client, name: str, error: str) -> None:
    """A taken or empty name redraws the page with the reason."""
    response = signed_in.post(reverse("boards:add"), {"name": name})
    assert response.status_code == 400
    assert error in response.content.decode()


def test_add_board_stops_at_the_limit(signed_in: Client, user: Any) -> None:
    """A full display says so instead of offering the form, and refuses another."""
    display = display_for(user)
    for position in range(1, MAX_BOARDS):
        BoardFactory.create(display=display, position=position)
    page = signed_in.get(reverse("boards:manage")).content.decode()
    assert f"holds up to {MAX_BOARDS} boards" in page
    assert f'action="{reverse("boards:add")}"' not in page
    response = signed_in.post(reverse("boards:add"), {"name": "One more"})
    assert response.status_code == 400
    assert display_for(user).boards.count() == MAX_BOARDS


def test_board_page_draws_the_board_and_its_forms(signed_in: Client, user: Any) -> None:
    """A board's page shows what it shows, its message to edit, and the palette."""
    board = post_message(display_for(user), "{r} Hello")
    content = signed_in.get(reverse("boards:board", args=[board.uuid])).content.decode()
    assert '<span class="face colour t-r">' in content
    assert '<span class="flap colour t-v">' in content
    assert "{r} Hello</textarea>" in content
    assert 'data-insert="{v}"' in content
    assert 'data-insert=":partcloud:" aria-label="Sun and cloud"' in content
    assert "Posted <time" in content


def test_message_saves_and_returns_to_the_board(signed_in: Client, user: Any) -> None:
    """Save puts the message on the board."""
    board = display_for(user).boards.get()
    response = signed_in.post(reverse("boards:message", args=[board.uuid]), {"text": "Sunny"})
    assert response.status_code == 302
    assert response["Location"] == reverse("boards:board", args=[board.uuid])
    board.refresh_from_db()
    assert board.message == "Sunny"


def test_clear_empties_the_board_whatever_the_box_says(signed_in: Client, user: Any) -> None:
    """Clear the board posts an empty message, ignoring the draft in the box."""
    board = post_message(display_for(user), "Old news")
    url = reverse("boards:message", args=[board.uuid])
    signed_in.post(url, {"text": "A draft", "clear": "1"})
    board.refresh_from_db()
    assert board.message == ""
    assert board.posted_at is None


def test_message_that_wont_fit_is_refused(signed_in: Client, user: Any) -> None:
    """A message longer than six rows is refused with the reason, and the draft kept."""
    board = display_for(user).boards.get()
    text = "\n".join(["row"] * 7)
    response = signed_in.post(reverse("boards:message", args=[board.uuid]), {"text": text})
    assert response.status_code == 400
    assert "needs 7 rows" in response.content.decode()
    assert "row\nrow" in response.content.decode()
    board.refresh_from_db()
    assert board.message == ""


def test_rename_board(signed_in: Client, user: Any) -> None:
    """A board takes a new name, and may change only its case."""
    board = display_for(user).boards.get()
    signed_in.post(reverse("boards:rename", args=[board.uuid]), {"name": "HOME"})
    board.refresh_from_db()
    assert board.name == "HOME"


def test_rename_refuses_a_taken_name(signed_in: Client, user: Any) -> None:
    """Two boards on a display can't share a name."""
    board = BoardFactory.create(display=display_for(user), name="News", position=1)
    response = signed_in.post(reverse("boards:rename", args=[board.uuid]), {"name": "home"})
    assert response.status_code == 400
    assert "already a board called home" in response.content.decode()
    board.refresh_from_db()
    assert board.name == "News"


def test_move_board_up_and_down(signed_in: Client, user: Any) -> None:
    """Moving a board swaps it with its neighbour, and a move past the end does nothing."""
    display = display_for(user)
    news = BoardFactory.create(display=display, name="News", position=1)
    url = reverse("boards:move", args=[news.uuid])

    def names() -> list[str]:
        return [b.name for b in display_for(user).boards.all()]

    response = signed_in.post(url, {"direction": "up"})
    assert response["Location"] == reverse("boards:manage") + "#boards"
    assert names() == ["News", "Home"]
    signed_in.post(url, {"direction": "up"})
    assert names() == ["News", "Home"]
    signed_in.post(url, {"direction": "down"})
    assert names() == ["Home", "News"]
    signed_in.post(url, {"direction": "sideways"})
    assert names() == ["Home", "News"]


def test_delete_asks_first(signed_in: Client, user: Any) -> None:
    """Delete board opens a page that asks; the board stays until you confirm."""
    board = BoardFactory.create(display=display_for(user), name="News", position=1)
    response = signed_in.get(reverse("boards:delete", args=[board.uuid]))
    assert response.status_code == 200
    assert "Delete News?" in response.content.decode()
    assert display_for(user).boards.filter(name="News").exists()


def test_delete_removes_the_board(signed_in: Client, user: Any) -> None:
    """Confirming deletes the board and goes back to the display."""
    board = BoardFactory.create(display=display_for(user), name="News", position=1)
    response = signed_in.post(reverse("boards:delete", args=[board.uuid]))
    assert response["Location"] == reverse("boards:manage")
    assert [b.name for b in display_for(user).boards.all()] == ["Home"]


def test_the_last_board_cant_be_deleted(signed_in: Client, user: Any) -> None:
    """A display keeps at least one board, and the page says why."""
    board = display_for(user).boards.get()
    url = reverse("boards:delete", args=[board.uuid])
    page = signed_in.get(url).content.decode()
    assert "a display needs at least one" in page
    assert "<form" not in page.split("<main")[1]
    response = signed_in.post(url)
    assert response.status_code == 400
    assert display_for(user).boards.count() == 1


def test_sound_starts_off_and_the_switch_says_so(signed_in: Client, user: Any) -> None:
    """A new display is quiet, and its switch is a button that turns the sound on."""
    response = signed_in.get(reverse("boards:manage"))
    content = response.content.decode()
    assert display_for(user).sound is False
    assert f'action="{reverse("boards:sound")}"' in content
    assert 'name="sound" value="on" role="switch" aria-checked="false"' in content


def test_sound_switch_turns_it_on_and_off(signed_in: Client, user: Any) -> None:
    """Each press saves the setting, comes back to the switch, and the TV is told."""
    url = reverse("boards:sound")
    response = signed_in.post(url, {"sound": "on"})
    assert response.status_code == 302
    assert response["Location"] == reverse("boards:manage") + "#sound"
    display = display_for(user)
    assert display.sound is True
    state = signed_in.get(reverse("tv:state", args=[display.uuid])).json()
    assert state["sound"] is True
    content = signed_in.get(reverse("boards:manage")).content.decode()
    assert 'name="sound" value="off" role="switch" aria-checked="true"' in content
    signed_in.post(url, {"sound": "off"})
    assert display_for(user).sound is False


def test_sound_switch_ignores_a_bad_value(signed_in: Client, user: Any) -> None:
    """Anything but on or off changes nothing."""
    display_for(user)
    assert signed_in.post(reverse("boards:sound"), {"sound": "loud"}).status_code == 302
    assert display_for(user).sound is False


def test_sound_switch_needs_sign_in(client: Client, user: Any) -> None:
    """Signed-out visitors are sent to sign in, and the setting is left alone."""
    display_for(user)
    response = client.post(reverse("boards:sound"), {"sound": "on"})
    assert response.status_code == 302
    assert "/signin/" in response["Location"]
    assert display_for(user).sound is False
    assert client.get(reverse("boards:sound")).status_code == 405


def test_tv_page_carries_the_sound_setting(client: Client, user: Any) -> None:
    """The TV knows the setting from its first draw, before it polls."""
    display = display_for(user)
    url = reverse("tv:board", args=[display.uuid])
    assert b'data-sound="off"' in client.get(url).content
    set_sound(display, True)
    assert b'data-sound="on"' in client.get(url).content


def test_sound_timing_shows_only_while_the_sound_is_on(signed_in: Client, user: Any) -> None:
    """There's nothing to time while the display is quiet; Replay is always there."""
    display = display_for(user)
    content = signed_in.get(reverse("boards:manage")).content.decode()
    assert reverse("boards:sound_delay") not in content
    assert f'action="{reverse("boards:replay")}"' in content
    set_sound(display, True)
    content = signed_in.get(reverse("boards:manage")).content.decode()
    assert f'action="{reverse("boards:sound_delay")}"' in content
    assert "0&nbsp;ms</output>" in content


def test_sound_timing_steps_up_and_down(signed_in: Client, user: Any) -> None:
    """Each button posts the next step; the ends of the range turn their button off."""
    display = display_for(user)
    set_sound(display, True)
    content = signed_in.get(reverse("boards:manage")).content.decode()
    assert 'name="sound_delay_ms" value="0" aria-label="Less delay" disabled' in content
    assert 'name="sound_delay_ms" value="50" aria-label="More delay">' in content
    response = signed_in.post(reverse("boards:sound_delay"), {"sound_delay_ms": "50"})
    assert response.status_code == 302
    assert response["Location"] == reverse("boards:manage") + "#sound-timing"
    assert display_for(user).sound_delay_ms == 50
    state = signed_in.get(reverse("tv:state", args=[display.uuid])).json()
    assert state["sound_delay_ms"] == 50
    set_sound_delay(display, 500)
    content = signed_in.get(reverse("boards:manage")).content.decode()
    assert 'name="sound_delay_ms" value="450" aria-label="Less delay">' in content
    assert 'name="sound_delay_ms" value="500" aria-label="More delay" disabled' in content


def test_sound_timing_ignores_a_bad_value(signed_in: Client, user: Any) -> None:
    """A value off the steps changes nothing."""
    display_for(user)
    for value in ("25", "600", "soon"):
        assert (
            signed_in.post(reverse("boards:sound_delay"), {"sound_delay_ms": value}).status_code
            == 302
        )
    assert display_for(user).sound_delay_ms == 0


def test_replay_tells_the_tv(signed_in: Client, user: Any) -> None:
    """Replay comes back to its button, and the TV's state carries the new count."""
    display = display_for(user)
    response = signed_in.post(reverse("boards:replay"))
    assert response.status_code == 302
    assert response["Location"] == reverse("boards:manage") + "#replay"
    state = signed_in.get(reverse("tv:state", args=[display.uuid])).json()
    assert state["replays"] == 1


@pytest.mark.parametrize("name", ["boards:sound_delay", "boards:replay"])
def test_sound_timing_and_replay_need_sign_in(client: Client, user: Any, name: str) -> None:
    """Signed-out visitors are sent to sign in, and nothing changes."""
    display_for(user)
    response = client.post(reverse(name), {"sound_delay_ms": "100"})
    assert "/signin/" in response["Location"]
    display = display_for(user)
    assert (display.sound_delay_ms, display.replays) == (0, 0)
    assert client.get(reverse(name)).status_code == 405


def test_tv_page_carries_the_sound_timing_and_replays(client: Client, user: Any) -> None:
    """The TV starts from the saved timing and replay count, before it polls."""
    display = display_for(user)
    set_sound_delay(display, 200)
    replay(display)
    content = client.get(reverse("tv:board", args=[display.uuid])).content
    assert b'data-sound-delay="200" data-replays="1"' in content

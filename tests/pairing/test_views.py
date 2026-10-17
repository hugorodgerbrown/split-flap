"""Tests for apps.pairing.views: a TV pairs, its owner types the code, the TV collects."""

from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.boards.services import display_for
from apps.pairing import services
from apps.pairing.models import TVPairing

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_rate_limits() -> None:
    """Start every test with fresh rate-limit counters."""
    cache.clear()


def _start(client: Client) -> dict[str, Any]:
    """Start a pairing as the TV app does and return its JSON."""
    response = client.post(reverse("pairing:start"))
    assert response.status_code == 201
    data: dict[str, Any] = response.json()
    return data


def test_a_tv_pairs_end_to_end(user: Any) -> None:
    """Start, enter the code on the phone, and the TV's next poll gets the link, once."""
    tv, phone = Client(enforce_csrf_checks=True), Client()
    started = _start(tv)
    assert started["poll_seconds"] == 3
    assert started["pair_url"].endswith(
        f"/app/display/pair/?code={started['code'].replace('-', '')}"
    )
    waiting = tv.get(started["poll_url"])
    assert waiting.json()["status"] == "waiting"
    assert waiting["Cache-Control"] == "no-store"

    phone.force_login(user)
    response = phone.post(reverse("pairing:pair"), {"code": started["code"].lower()})
    assert response.status_code == 302
    assert phone.get(response["Location"]).content.count(b"Your TV is linked") == 1

    display = display_for(user)
    paired = tv.get(started["poll_url"]).json()
    assert paired == {
        "status": "paired",
        "display_name": display.name,
        "display_url": f"http://testserver/d/{display.uuid}/",
    }
    assert tv.get(started["poll_url"]).status_code == 410


def test_the_code_reads_clearly() -> None:
    """Codes are six characters from an alphabet with no look-alikes, shown with a dash."""
    started = services.start()
    assert len(started.code) == services.CODE_LENGTH
    assert not set(started.code) & set("0O1IL")
    assert services.format_code("K7Q4MD") == "K7Q-4MD"


def test_only_hashes_are_stored() -> None:
    """Neither the code nor the token is in the row."""
    started = services.start()
    row = TVPairing.objects.get()
    assert started.code not in (row.code_hash, row.token_hash)
    assert started.token not in (row.code_hash, row.token_hash)


def test_unknown_token_is_404(client: Client) -> None:
    """A made-up token finds nothing."""
    assert client.get(reverse("pairing:poll", args=["nope"])).status_code == 404


def test_expired_pairing_is_410(client: Client) -> None:
    """A code nobody entered in time is gone."""
    started = services.start()
    TVPairing.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    response = client.get(reverse("pairing:poll", args=[started.token]))
    assert response.status_code == 410
    assert response.json() == {"status": "expired"}


def test_start_is_post_only_and_rate_limited(client: Client) -> None:
    """GET is refused; the twenty-first start in an hour from one address is too."""
    assert client.get(reverse("pairing:start")).status_code == 405
    for _ in range(20):
        _start(client)
    assert client.post(reverse("pairing:start")).status_code == 429


def test_pair_page_needs_sign_in(client: Client) -> None:
    """Signed-out visitors are sent to sign in first."""
    assert client.get(reverse("pairing:pair")).status_code == 302


def test_pair_page_fills_in_the_code_from_the_qr_link(signed_in: Client) -> None:
    """Scanning the TV's QR code opens the page with the code already typed."""
    response = signed_in.get(reverse("pairing:pair"), {"code": "K7Q4MD"})
    assert response.status_code == 200
    assert b'value="K7Q4MD"' in response.content


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("ABC", b"A code is 6 letters and numbers"),
        ("ABCDEF", b"isn&#x27;t waiting to be linked"),
    ],
)
def test_a_wrong_code_says_so(signed_in: Client, code: str, message: bytes) -> None:
    """A malformed or unknown code is refused with a reason."""
    response = signed_in.post(reverse("pairing:pair"), {"code": code})
    assert response.status_code == 400
    assert message in response.content


def test_a_code_works_once(signed_in: Client, user: Any) -> None:
    """Once claimed, the same code can't be claimed again."""
    started = services.start()
    assert services.claim(started.code, display_for(user)) is not None
    response = signed_in.post(reverse("pairing:pair"), {"code": started.code})
    assert response.status_code == 400


def test_an_expired_code_cant_be_claimed(user: Any) -> None:
    """A code past its ten minutes links nothing."""
    started = services.start()
    TVPairing.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert services.claim(started.code, display_for(user)) is None


def test_collect_needs_a_claim() -> None:
    """An unclaimed pairing hands over nothing."""
    assert services.collect(services.start().pairing) is None


def test_guesses_are_rate_limited(signed_in: Client) -> None:
    """The eleventh try in ten minutes is refused, even with a good code."""
    for _ in range(10):
        signed_in.post(reverse("pairing:pair"), {"code": "ABCDEF"})
    started = services.start()
    response = signed_in.post(reverse("pairing:pair"), {"code": started.code})
    assert response.status_code == 429
    assert TVPairing.objects.get().claimed_at is None


def test_display_page_links_to_pairing(signed_in: Client) -> None:
    """The display page offers to link a TV app."""
    response = signed_in.get(reverse("boards:manage"))
    assert reverse("pairing:pair").encode() in response.content

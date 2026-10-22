"""Tests for the Raspberry Pi kiosk (raspberry-pi/riffle_kiosk.py), with the network faked."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import threading
import urllib.request
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from django.test import Client

SERVER = "https://riffle.example"
UUID = "0b7c3a52-5d0e-4c55-9a3e-3f1d2c4b5a69"
BOARD = f"{SERVER}/d/{UUID}/"
POLL = f"{SERVER}/d/pair/tok/"
STARTED = {
    "code": "K7Q-4MD",
    "pair_url": f"{SERVER}/app/display/pair/?code=K7Q4MD",
    "poll_url": POLL,
    "poll_seconds": 3,
}


KIOSK = Path(__file__).resolve().parents[2] / "raspberry-pi" / "riffle_kiosk.py"


def _load() -> ModuleType:
    """Import the kiosk from its file: it ships to the Pi on its own, not as a package."""
    path = KIOSK
    spec = importlib.util.spec_from_file_location("riffle_kiosk", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["riffle_kiosk"] = module
    spec.loader.exec_module(module)
    return module


rk = _load()


def test_the_kiosk_runs_on_the_python_a_pi_ships() -> None:
    """The kiosk parses as Python 3.11, which Raspberry Pi OS Bookworm ships."""
    ast.parse(KIOSK.read_text(), filename=str(KIOSK), feature_version=(3, 11))


class FakeServer:
    """Answers the kiosk's requests from a table, and records them."""

    def __init__(self) -> None:
        self.answers: dict[tuple[str, str], tuple[int, bytes] | Exception] = {}
        self.calls: list[tuple[str, str]] = []

    def answer(self, method: str, url: str, status: int, body: object = None) -> None:
        """Answer ``method url`` with ``status`` and ``body`` as JSON."""
        self.answers[(method, url)] = (status, json.dumps(body).encode() if body else b"")

    def fail(self, method: str, url: str) -> None:
        """Make ``method url`` fail as if the network were down."""
        self.answers[(method, url)] = OSError("network down")

    def __call__(self, url: str, method: str) -> tuple[int, bytes]:
        """Answer one request."""
        self.calls.append((method, url))
        answer = self.answers[(method, url)]
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def server() -> FakeServer:
    """A fake Riffle server."""
    return FakeServer()


@pytest.fixture
def kiosk(server: FakeServer, tmp_path: Path) -> Any:
    """A kiosk talking to the fake server, keeping its state in a temporary directory."""
    return rk.Kiosk(
        rk.Api(SERVER, fetch=server), rk.Store(tmp_path), qr=lambda text: f"<svg>{text}</svg>"
    )


# --- Links ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (BOARD, True),
        (f"https://RIFFLE.example:443/d/{UUID}/", True),
        (f"http://riffle.example/d/{UUID}/", False),
        (f"https://riffle.example:8443/d/{UUID}/", False),
        (f"https://evil.example/d/{UUID}/", False),
        (f"{BOARD}?next=/", False),
        (f"{BOARD}#x", False),
        (f"{SERVER}/d/{UUID}", False),
        (f"{SERVER}/app/", False),
        (f"https://riffle.example:bad/d/{UUID}/", False),
        ("javascript:alert(1)", False),
    ],
)
def test_only_a_display_board_on_our_server_is_opened(url: str, expected: bool) -> None:
    """The kiosk opens a display's board on its own server, and nothing else."""
    assert rk.is_display_url(url, SERVER) is expected


def test_the_typed_address_has_no_scheme() -> None:
    """People type the pair page's address without https://."""
    assert rk.typed_pair_address(SERVER + "/") == "riffle.example/app/display/pair/"


# --- What the server says --------------------------------------------------------


def test_poll_seconds_are_kept_sensible() -> None:
    """A poll interval from the server is held between 1 and 30 seconds."""
    assert rk.parse_started({**STARTED, "poll_seconds": 0}).poll_seconds == 1
    assert rk.parse_started({**STARTED, "poll_seconds": 600}).poll_seconds == 30
    assert (
        rk.parse_started({k: v for k, v in STARTED.items() if k != "poll_seconds"}).poll_seconds
        == 3
    )


@pytest.mark.parametrize(
    ("status", "data", "expected"),
    [
        (200, {"status": "waiting"}, "waiting"),
        (404, {"status": "unknown"}, "expired"),
        (410, {"status": "expired"}, "expired"),
        (200, None, "expired"),
        (200, {"status": "something new"}, "expired"),
        (200, {"status": "paired", "display_url": "https://evil.example/"}, "expired"),
    ],
)
def test_poll_answers(status: int, data: dict[str, Any] | None, expected: str) -> None:
    """Each answer to a poll means waiting or starting again."""
    assert rk.parse_poll(status, data, SERVER) == expected


def test_a_paired_answer_names_the_display() -> None:
    """A claimed code hands over the display's board link and name."""
    answer = rk.parse_poll(
        200, {"status": "paired", "display_url": BOARD, "display_name": "Kitchen"}, SERVER
    )
    assert answer == rk.Paired(BOARD, "Kitchen")


def test_the_kiosk_reads_the_real_pairing_endpoints(
    db: None, client: Client, signed_in: Client
) -> None:
    """The kiosk understands what apps/pairing actually answers, from start to paired."""
    tv = Client()
    response = tv.post("/d/pair/")
    started = rk.parse_started(response.json())
    server = "http://testserver"
    poll_path = started.poll_url.removeprefix(server)
    waiting = tv.get(poll_path)
    assert rk.parse_poll(waiting.status_code, waiting.json(), server) == rk.WAITING

    signed_in.post("/app/display/pair/", {"code": started.code})
    paired = tv.get(poll_path)
    answer = rk.parse_poll(paired.status_code, paired.json(), server)
    assert isinstance(answer, rk.Paired)
    assert rk.is_display_url(answer.display_url, server)


# --- The API ---------------------------------------------------------------------


def test_start_returns_the_code(server: FakeServer) -> None:
    """Starting a pairing returns the code to show."""
    server.answer("POST", f"{SERVER}/d/pair/", 201, STARTED)
    assert rk.Api(SERVER, fetch=server).start().code == "K7Q-4MD"


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (429, {"error": "rate_limited"}, "Too many"),
        (500, None, "HTTP 500"),
        (201, {"code": "K7Q-4MD"}, "not understood"),
    ],
)
def test_start_fails_cleanly(server: FakeServer, status: int, body: object, error: str) -> None:
    """A refused or garbled start raises an error the kiosk knows how to wait out."""
    server.answer("POST", f"{SERVER}/d/pair/", status, body)
    with pytest.raises(OSError, match=error):
        rk.Api(SERVER, fetch=server).start()


def test_poll_never_leaves_our_server(server: FakeServer) -> None:
    """A poll link on another server is treated as expired and never fetched."""
    assert rk.Api(SERVER, fetch=server).poll("https://evil.example/d/pair/tok/") == rk.EXPIRED
    assert server.calls == []


def test_a_server_error_while_polling_is_retried(server: FakeServer) -> None:
    """A 5xx while polling raises, so the kiosk keeps the code and polls again."""
    server.answer("GET", POLL, 502)
    with pytest.raises(OSError, match="HTTP 502"):
        rk.Api(SERVER, fetch=server).poll(POLL)


@pytest.mark.parametrize(("status", "expected"), [(200, "ok"), (404, "gone"), (503, "offline")])
def test_check_reports_the_board(server: FakeServer, status: int, expected: str) -> None:
    """Checking the board tells loaded, deleted and unreachable apart."""
    server.answer("GET", BOARD, status)
    assert rk.Api(SERVER, fetch=server).check(BOARD) == expected


def test_check_is_offline_without_a_network(server: FakeServer) -> None:
    """No network means offline, not deleted."""
    server.fail("GET", BOARD)
    assert rk.Api(SERVER, fetch=server).check(BOARD) == "offline"


# --- Remembering the display ---------------------------------------------------------


def test_the_store_survives_a_restart(tmp_path: Path) -> None:
    """A saved display is there for the next Store, and gone once cleared."""
    rk.Store(tmp_path / "riffle").save(rk.Paired(BOARD, "Kitchen"))
    assert rk.Store(tmp_path / "riffle").load() == rk.Paired(BOARD, "Kitchen")
    rk.Store(tmp_path / "riffle").clear()
    assert rk.Store(tmp_path / "riffle").load() is None


@pytest.mark.parametrize("content", ["not json", "[]", '{"display_url": 3}'])
def test_a_damaged_store_is_not_linked(tmp_path: Path, content: str) -> None:
    """A damaged file means pairing again, not crashing."""
    (tmp_path / "display.json").write_text(content)
    assert rk.Store(tmp_path).load() is None


# --- The kiosk, step by step ---------------------------------------------------------


def test_pairing_from_start_to_board(kiosk: Any, server: FakeServer) -> None:
    """An unlinked Pi shows a code, waits, saves the display, checks it, then opens it."""
    server.answer("POST", f"{SERVER}/d/pair/", 201, STARTED)
    assert kiosk.step() == 3
    assert kiosk.state == {
        "state": "pairing",
        "code": "K7Q-4MD",
        "address": "riffle.example/app/display/pair/",
    }
    assert kiosk.qr == f"<svg>{STARTED['pair_url']}</svg>"

    server.answer("GET", POLL, 200, {"status": "waiting"})
    assert kiosk.step() == 3

    server.answer(
        "GET", POLL, 200, {"status": "paired", "display_url": BOARD, "display_name": "Kitchen"}
    )
    assert kiosk.step() == 0
    assert kiosk.store.load() == rk.Paired(BOARD, "Kitchen")

    server.answer("GET", BOARD, 200)
    assert kiosk.step() == rk.IDLE_SECONDS
    assert kiosk.state == {"state": "ready", "display_url": BOARD, "display_name": "Kitchen"}


def test_a_showing_board_is_not_checked_again_until_the_page_reloads(
    kiosk: Any, server: FakeServer
) -> None:
    """Once the board is showing, nothing is fetched until the start page loads again."""
    kiosk.store.save(rk.Paired(BOARD, "Kitchen"))
    server.answer("GET", BOARD, 200)
    kiosk.step()
    kiosk.step()
    assert server.calls == [("GET", BOARD)]

    kiosk.reload()
    assert kiosk.state == {"state": "starting"}
    kiosk.step()
    assert server.calls == [("GET", BOARD), ("GET", BOARD)]


def test_an_unreachable_board_is_retried_with_backoff(kiosk: Any, server: FakeServer) -> None:
    """While the server can't be reached, the kiosk says so and waits longer each time."""
    kiosk.store.save(rk.Paired(BOARD, "Kitchen"))
    server.fail("GET", BOARD)
    delays = [kiosk.step() for _ in range(6)]
    assert delays == [5, 10, 20, 40, 60, 60]
    assert kiosk.state == {"state": "offline"}

    server.answer("GET", BOARD, 200)
    kiosk.step()
    assert kiosk.state["state"] == "ready"
    kiosk.reload()
    server.fail("GET", BOARD)
    assert kiosk.step() == 5


def test_a_deleted_display_pairs_again(kiosk: Any, server: FakeServer) -> None:
    """When the display has been deleted, the Pi forgets it and asks for a new code."""
    kiosk.store.save(rk.Paired(BOARD, "Kitchen"))
    server.answer("GET", BOARD, 404)
    assert kiosk.step() == 0
    assert kiosk.store.load() is None
    server.answer("POST", f"{SERVER}/d/pair/", 201, STARTED)
    kiosk.step()
    assert kiosk.state["state"] == "pairing"


def test_a_link_to_another_server_is_forgotten(kiosk: Any, server: FakeServer) -> None:
    """A saved link that isn't a board on this server is never opened."""
    kiosk.store.save(rk.Paired("https://evil.example/", "Evil"))
    assert kiosk.step() == 0
    assert kiosk.store.load() is None
    assert server.calls == []


def test_too_many_codes_waits_a_minute(kiosk: Any, server: FakeServer) -> None:
    """When the server rate limits pairing, the kiosk says so and waits a minute."""
    server.answer("POST", f"{SERVER}/d/pair/", 429, {"error": "rate_limited"})
    assert kiosk.step() == rk.RATE_LIMITED_RETRY_SECONDS
    assert kiosk.state == {"state": "busy"}


def test_no_network_while_pairing(kiosk: Any, server: FakeServer) -> None:
    """Without a network the kiosk says it is reconnecting, then keeps polling the same code."""
    server.fail("POST", f"{SERVER}/d/pair/")
    assert kiosk.step() == 5
    assert kiosk.state == {"state": "offline"}

    server.answer("POST", f"{SERVER}/d/pair/", 201, STARTED)
    kiosk.step()
    server.fail("GET", POLL)
    assert kiosk.step() == 3
    assert kiosk.state["code"] == "K7Q-4MD"


def test_an_expired_code_is_replaced(kiosk: Any, server: FakeServer) -> None:
    """When a code runs out, the kiosk asks for a new one."""
    server.answer("POST", f"{SERVER}/d/pair/", 201, STARTED)
    kiosk.step()
    server.answer("GET", POLL, 410, {"status": "expired"})
    assert kiosk.step() == 0
    kiosk.step()
    assert server.calls.count(("POST", f"{SERVER}/d/pair/")) == 2


def test_run_forever_survives_a_surprise(kiosk: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unexpected error in a step is logged and retried, not fatal."""
    calls = []

    def step() -> float:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("surprise")
        raise SystemExit

    monkeypatch.setattr(kiosk, "step", step)
    monkeypatch.setattr(kiosk._wake, "wait", lambda delay: True)
    with pytest.raises(SystemExit):
        kiosk.run_forever()
    assert len(calls) == 2


# --- The start page --------------------------------------------------------------------


@pytest.fixture
def start_page(kiosk: Any) -> Iterator[str]:
    """The start page, served on a free local port."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), rk.make_handler(kiosk))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _get(url: str) -> tuple[int, str, str]:
    """Fetch ``url`` and return its status, content type and body."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310  # nosemgrep (a local test server)
            return response.status, response.headers["Content-Type"], response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, "", ""


def test_the_start_page_and_its_parts(start_page: str, kiosk: Any) -> None:
    """The page, its stylesheet, script, QR code and state are served, and nothing else."""
    status, kind, body = _get(start_page + "/")
    assert (status, kind) == (200, "text/html; charset=utf-8")
    assert '<script src="/kiosk.js" defer>' in body
    assert _get(start_page + "/kiosk.css")[1] == "text/css; charset=utf-8"
    assert "location.replace" in _get(start_page + "/kiosk.js")[2]
    kiosk.qr = "<svg/>"
    assert _get(start_page + "/qr.svg?code=K7Q-4MD")[1:] == ("image/svg+xml", "<svg/>")
    assert json.loads(_get(start_page + "/state")[2]) == {"state": "starting"}
    assert _get(start_page + "/admin/")[0] == 404


def test_loading_the_start_page_checks_the_board_again(start_page: str, kiosk: Any) -> None:
    """A reboot or browser restart loads the start page, which checks the board again."""
    kiosk._show("ready", display_url=BOARD, display_name="Kitchen")
    _get(start_page + "/")
    assert kiosk.state == {"state": "starting"}


# --- Talking to a real HTTP server -------------------------------------------------------


class _Origin(BaseHTTPRequestHandler):
    """A tiny server: a redirect, a 404 and a JSON answer."""

    def do_GET(self) -> None:
        """Answer by path."""
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://evil.example/")
            self.end_headers()
        elif self.path == "/missing":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"status": "unknown"}')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "waiting"}')

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the test output quiet."""


@pytest.fixture
def origin() -> Iterator[str]:
    """A local server to fetch from."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Origin)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def test_fetch_never_follows_a_redirect(origin: str) -> None:
    """A redirect comes back as its own status, never followed to another server."""
    assert rk.fetch(origin + "/redirect", "GET")[0] == 302


def test_fetch_returns_error_statuses_and_bodies(origin: str) -> None:
    """A 404 comes back with its body, not as an exception."""
    assert rk.fetch(origin + "/missing", "GET") == (404, b'{"status": "unknown"}')
    assert rk.fetch(origin + "/", "GET") == (200, b'{"status": "waiting"}')


def test_fetch_refuses_other_schemes() -> None:
    """Only http(s) URLs are fetched."""
    with pytest.raises(OSError, match="Not an http"):
        rk.fetch("file:///etc/passwd", "GET")


# --- The QR code and the commands ---------------------------------------------------------


def test_no_qrencode_means_no_qr_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without qrencode the code is shown alone."""
    monkeypatch.setattr(rk.shutil, "which", lambda name: None)
    assert rk.qr_svg("https://riffle.example/") == ""


def test_qrencode_draws_the_svg(monkeypatch: pytest.MonkeyPatch) -> None:
    """The SVG from qrencode is returned without its XML prolog."""

    class Done:
        stdout = b'<?xml version="1.0"?>\n<svg width="10"></svg>'

    seen: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> Done:
        seen.append(args)
        return Done()

    monkeypatch.setattr(rk.shutil, "which", lambda name: "/usr/bin/qrencode")
    monkeypatch.setattr(rk.subprocess, "run", run)
    assert rk.qr_svg("https://riffle.example/") == '<svg width="10"></svg>'
    assert seen[0][-2:] == ["--", "https://riffle.example/"]


def test_a_failing_qrencode_means_no_qr_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """If qrencode fails, the code is shown alone."""

    def fail(*args: Any, **kwargs: Any) -> None:
        raise rk.subprocess.CalledProcessError(1, "qrencode")

    monkeypatch.setattr(rk.shutil, "which", lambda name: "/usr/bin/qrencode")
    monkeypatch.setattr(rk.subprocess, "run", fail)
    assert rk.qr_svg("x") == ""


def test_status_and_unlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Status exits 1 until linked; unlink forgets the display and restarts the browser."""
    monkeypatch.setenv("RIFFLE_SERVER", SERVER)
    monkeypatch.setenv("RIFFLE_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(rk, "fetch", lambda url, method: (200, b""))
    restarted: list[bool] = []
    monkeypatch.setattr(rk, "restart_display", lambda: restarted.append(True))
    assert rk.main(["status"]) == 1

    rk.Store(tmp_path).save(rk.Paired(BOARD, "Kitchen"))
    assert rk.main(["status"]) == 0
    assert rk.main(["unlink"]) == 0
    assert rk.Store(tmp_path).load() is None
    assert restarted == [True]


def test_status_says_when_the_board_cannot_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The status command still succeeds when linked but offline."""
    monkeypatch.setattr(rk.Api, "check", lambda self, url: "offline")
    rk.Store(tmp_path).save(rk.Paired(BOARD, "Kitchen"))
    assert rk.status(SERVER, tmp_path) == 0


def test_restart_display_without_systemd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Off a Pi (no systemctl), restarting does nothing."""
    monkeypatch.setattr(rk.shutil, "which", lambda name: None)
    rk.restart_display()


def test_restart_display_restarts_both_services(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unlinking restarts the kiosk and the browser, so the TV shows a new code at once."""
    seen: list[list[str]] = []
    monkeypatch.setattr(rk.shutil, "which", lambda name: "/usr/bin/systemctl")
    monkeypatch.setattr(rk.subprocess, "run", lambda args, **kwargs: seen.append(args))
    rk.restart_display()
    assert seen == [
        ["/usr/bin/systemctl", "restart", "riffle-kiosk.service", "riffle-display.service"]
    ]

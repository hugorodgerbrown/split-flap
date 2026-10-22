"""Riffle's Raspberry Pi kiosk: pair with a display, then open its board full screen.

The Pi's browser (Chromium, full screen under cage) always starts on
``http://127.0.0.1:8737/``, which this module serves. That page shows a
pairing code until the Pi is linked to a display, "Reconnecting…" while
the server can't be reached, and otherwise sends the browser to the
display's own board page. It is the Android TV app's native shell again
(docs/decisions/the-tv-app-is-a-shell-around-the-board.md), for a Pi:
the board itself is always the web page, never redrawn here.

Standard library only, so it runs on the Python that Raspberry Pi OS
ships (3.11 or later) with nothing to install. Commands:

    riffle-kiosk serve    the start page (run by riffle-kiosk.service)
    riffle-kiosk status   which display this Pi shows
    riffle-kiosk unlink   forget it and show a new pairing code
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

VERSION = "0.1.0"
DEFAULT_SERVER = "https://split-flap.ultraniche.ai"
DEFAULT_STATE_DIR = "/var/lib/riffle"
HOST = "127.0.0.1"
PORT = 8737
TIMEOUT_SECONDS = 10
FIRST_RETRY_SECONDS = 5.0
MAX_RETRY_SECONDS = 60.0
RATE_LIMITED_RETRY_SECONDS = 60.0
# While the board is showing, how often to check its display still exists. The
# board page polls by itself, but never leaves a deleted display.
RECHECK_SECONDS = 300.0

DISPLAY_PATH = re.compile(r"^/d/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/$")


# --- What the server says (apps/pairing/views.py) ----------------------------


@dataclass(frozen=True)
class Started:
    """A started pairing: the code to show, the link for its QR code, and where to poll."""

    code: str
    pair_url: str
    poll_url: str
    poll_seconds: int


@dataclass(frozen=True)
class Paired:
    """The code was typed: show this display from now on."""

    display_url: str
    display_name: str


WAITING = "waiting"
EXPIRED = "expired"
PollAnswer = Paired | str


def _origin(url: str) -> tuple[str, str, int] | None:
    """Return ``url``'s scheme, host and port, or None if it isn't an http(s) URL."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https") or not parts.hostname:
        return None
    return scheme, parts.hostname.lower(), port or (443 if scheme == "https" else 80)


def is_own_page(url: str, server: str) -> bool:
    """Return True when ``url`` is on our own server."""
    own = _origin(server)
    return own is not None and _origin(url) == own


def is_display_url(url: str, server: str) -> bool:
    """Return True for a display's board on our own server (``<server>/d/<uuid>/``) only."""
    if not is_own_page(url, server):
        return False
    parts = urlsplit(url)
    return not parts.query and not parts.fragment and bool(DISPLAY_PATH.match(parts.path))


def typed_pair_address(server: str) -> str:
    """Return the address people type on their phone: the pair page without the scheme."""
    return f"{server.split('://', 1)[-1].rstrip('/')}/app/display/pair/"


def parse_started(data: dict[str, Any]) -> Started:
    """Read the answer to ``POST /d/pair/``."""
    return Started(
        code=str(data["code"]),
        pair_url=str(data["pair_url"]),
        poll_url=str(data["poll_url"]),
        poll_seconds=min(max(int(data.get("poll_seconds", 3)), 1), 30),
    )


def parse_poll(status: int, data: dict[str, Any] | None, server: str) -> PollAnswer:
    """Read the answer to ``GET /d/pair/<token>/``, given its HTTP status."""
    if status in (404, 410) or data is None:
        return EXPIRED
    answer = data.get("status")
    if answer == "waiting":
        return WAITING
    if answer == "paired":
        url = str(data.get("display_url", ""))
        if is_display_url(url, server):
            return Paired(url, str(data.get("display_name", "")))
    return EXPIRED


# --- Talking to the server ---------------------------------------------------


class RateLimitedError(OSError):
    """The server asked us to slow down."""


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Refuse redirects, so every request stays on the server it was meant for."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        """Return nothing, so urllib raises the redirect as an HTTPError."""


Fetch = Callable[[str, str], tuple[int, bytes]]


def fetch(url: str, method: str) -> tuple[int, bytes]:
    """Make one request and return its status and body; raise OSError if it can't be made."""
    if _origin(url) is None:
        raise OSError(f"Not an http(s) URL: {url}")
    request = urllib.request.Request(  # noqa: S310  # nosemgrep (the scheme is checked above)
        url,
        method=method,
        data=b"" if method == "POST" else None,
        headers={"Accept": "application/json", "User-Agent": f"RiffleKiosk/{VERSION}"},
    )
    opener = urllib.request.build_opener(_NoRedirects)
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:  # nosemgrep
            return int(response.status), response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def _json(body: bytes) -> dict[str, Any] | None:
    """Return ``body`` as a JSON object, or None if it isn't one."""
    try:
        data = json.loads(body)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


class Api:
    """The server's pairing endpoints, and a check that a display's board still loads."""

    def __init__(self, server: str, fetch: Fetch = fetch) -> None:
        self.server = server.rstrip("/")
        self._fetch = fetch

    def start(self) -> Started:
        """Start a pairing and return its code."""
        status, body = self._fetch(f"{self.server}/d/pair/", "POST")
        if status == 429:
            raise RateLimitedError("Too many pairing requests")
        data = _json(body)
        if status != 201 or data is None:
            raise OSError(f"Pairing failed to start: HTTP {status}")
        try:
            return parse_started(data)
        except (KeyError, TypeError, ValueError) as error:
            raise OSError("Pairing answer was not understood") from error

    def poll(self, poll_url: str) -> PollAnswer:
        """Ask whether the code has been typed."""
        if not is_own_page(poll_url, self.server):
            return EXPIRED
        status, body = self._fetch(poll_url, "GET")
        if status >= 500:
            raise OSError(f"Server error: HTTP {status}")
        return parse_poll(status, _json(body), self.server)

    def check(self, display_url: str) -> str:
        """Return "ok" if the board loads, "gone" if the display was deleted, else "offline"."""
        try:
            status, _ = self._fetch(display_url, "GET")
        except OSError:
            return "offline"
        if status == 200:
            return "ok"
        return "gone" if status == 404 else "offline"


# --- Remembering the display -------------------------------------------------


class Store:
    """The linked display, kept in one small JSON file that survives reboots."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / "display.json"

    def load(self) -> Paired | None:
        """Return the linked display, or None."""
        try:
            data = _json(self.path.read_bytes())
        except OSError:
            return None
        if data is None or not isinstance(data.get("display_url"), str):
            return None
        return Paired(data["display_url"], str(data.get("display_name", "")))

    def save(self, display: Paired) -> None:
        """Link this Pi to ``display``, writing the whole file so a power cut can't tear it."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        partial = self.path.with_suffix(".tmp")
        payload = {"display_url": display.display_url, "display_name": display.display_name}
        partial.write_text(json.dumps(payload))
        partial.replace(self.path)

    def clear(self) -> None:
        """Forget the linked display."""
        self.path.unlink(missing_ok=True)


# --- The QR code -------------------------------------------------------------


def qr_svg(text: str) -> str:
    """Return ``text`` as an SVG QR code drawn by ``qrencode``, or "" if it isn't installed."""
    qrencode = shutil.which("qrencode")
    if qrencode is None:
        return ""
    try:
        result = subprocess.run(  # noqa: S603  # nosemgrep (a fixed program; the text is one argument)
            [qrencode, "--type=SVG", "--margin=2", "--output=-", "--", text],
            capture_output=True,
            check=True,
            timeout=TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("qrencode failed; showing the code without a QR code")
        return ""
    svg = result.stdout.decode("utf-8", "replace")
    # Drop the XML prolog so the SVG can sit inside the page.
    return svg[svg.find("<svg") :] if "<svg" in svg else ""


# --- The kiosk ---------------------------------------------------------------


class Kiosk:
    """What the start page shows, kept up to date by one worker thread.

    The worker runs ``step()`` in a loop. Each step does one thing (start a
    pairing, poll it, or check the board loads) and returns how long to wait
    before the next; loading the start page wakes it early.
    """

    def __init__(
        self,
        api: Api,
        store: Store,
        qr: Callable[[str], str] = qr_svg,
        leave_board: Callable[[], None] = lambda: None,
    ) -> None:
        self.api = api
        self.store = store
        self._qr = qr
        self._leave_board = leave_board
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._state: dict[str, Any] = {"state": "starting"}
        self._pairing: Started | None = None
        self._retry = FIRST_RETRY_SECONDS
        # The current pairing's QR code, as SVG, served at /qr.svg.
        self.qr = ""

    @property
    def state(self) -> dict[str, Any]:
        """Return a copy of what the start page should show."""
        with self._lock:
            return dict(self._state)

    def _show(self, state: str, **extra: Any) -> None:
        """Set what the start page should show."""
        with self._lock:
            self._state = {"state": state, **extra}

    def _backoff(self) -> float:
        """Return the next retry delay, doubling it each time up to a minute."""
        delay = self._retry
        self._retry = min(self._retry * 2, MAX_RETRY_SECONDS)
        return delay

    def reload(self) -> None:
        """The start page loaded again (a reboot or a browser restart): check the board afresh."""
        with self._lock:
            if self._state.get("state") == "ready":
                self._state = {"state": "starting"}
        self._wake.set()

    def step(self) -> float:
        """Do the next thing and return how many seconds to wait before the next step."""
        display = self.store.load()
        if display is not None:
            return self._step_linked(display)
        if self._pairing is None:
            return self._step_start()
        return self._step_poll(self._pairing)

    def _step_linked(self, display: Paired) -> float:
        """Check the linked display's board loads, then hand it to the browser."""
        if not is_display_url(display.display_url, self.api.server):
            logger.warning("Forgetting a display link that isn't on %s", self.api.server)
            self.store.clear()
            return 0
        showing = self.state.get("state") == "ready"
        result = self.api.check(display.display_url)
        if result == "ok":
            self._retry = FIRST_RETRY_SECONDS
            self._show("ready", display_url=display.display_url, display_name=display.display_name)
            return RECHECK_SECONDS
        if result == "gone":
            logger.info("The display was deleted; pairing again")
            self.store.clear()
            self._show("starting")
            if showing:
                # The browser is on the deleted board: send it back to the start page.
                self._leave_board()
            return 0
        if showing:
            # The board rides out an outage by itself; check again later.
            return RECHECK_SECONDS
        self._show("offline")
        return self._backoff()

    def _step_start(self) -> float:
        """Ask the server for a pairing code."""
        try:
            started = self.api.start()
        except RateLimitedError:
            self._show("busy")
            return RATE_LIMITED_RETRY_SECONDS
        except OSError as error:
            logger.info("Can't start pairing: %s", error)
            self._show("offline")
            return self._backoff()
        self._retry = FIRST_RETRY_SECONDS
        self._pairing = started
        self.qr = self._qr(started.pair_url)
        self._show("pairing", code=started.code, address=typed_pair_address(self.api.server))
        return started.poll_seconds

    def _step_poll(self, started: Started) -> float:
        """Ask whether the code has been typed yet."""
        try:
            answer = self.api.poll(started.poll_url)
        except OSError as error:
            logger.info("Can't poll the pairing: %s", error)
            return started.poll_seconds
        if isinstance(answer, Paired):
            logger.info("Linked to %s", answer.display_name or answer.display_url)
            self.store.save(answer)
            self._pairing = None
            self._show("starting")
            return 0
        if answer == EXPIRED:
            self._pairing = None
            return 0
        return started.poll_seconds

    def run_forever(self) -> None:
        """Run steps until the process ends; a step that fails unexpectedly is retried."""
        while True:
            try:
                delay = self.step()
            except Exception:
                logger.exception("Unexpected error; trying again")
                delay = self._backoff()
            self._wake.wait(delay)
            self._wake.clear()


# --- The start page ----------------------------------------------------------

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Riffle</title>
<link rel="stylesheet" href="/kiosk.css">
<script src="/kiosk.js" defer></script>
</head>
<body>
<main id="pair" class="panel" hidden>
  <h1>Link this TV to your display</h1>
  <div class="steps">
    <div>
      <p class="muted">On your phone, go to</p>
      <p id="address" class="address"></p>
      <p class="muted">and type this code</p>
      <p id="code" class="code">······</p>
    </div>
    <figure>
      <img id="qr" class="qr" alt="">
      <figcaption class="muted">Or scan this with your phone's camera.</figcaption>
    </figure>
  </div>
  <p class="muted status">Waiting for the code. A new one appears every ten minutes.</p>
</main>
<p id="message" class="message">Starting…</p>
</body>
</html>
"""

STYLE = """:root {
  --frame: #1c1b1a; --well: #090909; --ink: #eeeae1; --ink-muted: #a8a397;
  --engrave: #4b4841; --tile-yellow: #f5c22b;
  --font: "Barlow", "Helvetica Neue", "DejaVu Sans", Arial, sans-serif;
}
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body {
  display: grid; place-items: center; background: var(--well); color: var(--ink);
  font: 500 2.2vh/1.4 var(--font); cursor: none; overflow: hidden;
}
[hidden] { display: none !important; }
.panel {
  padding: 5vh 6vh; background: var(--frame); border: 1px solid var(--engrave);
  border-radius: 2vh; text-align: center;
}
h1 { margin: 0 0 4vh; font-size: 4.2vh; font-weight: 600; }
.steps { display: flex; gap: 6vh; align-items: center; text-align: left; }
p { margin: 0; }
.muted { color: var(--ink-muted); }
.address { margin: 0.5vh 0 3vh; font-size: 3vh; font-weight: 600; }
.code {
  display: inline-block;
  margin-top: 1vh; padding: 1.5vh 3vh; background: var(--well); border-radius: 1vh;
  color: var(--tile-yellow); font: 700 7vh/1 ui-monospace, "DejaVu Sans Mono", monospace;
  letter-spacing: 0.15em;
}
figure { margin: 0; width: 26vh; text-align: center; font-size: 1.8vh; }
.qr {
  display: block; width: 26vh; height: 26vh; margin-bottom: 1.5vh;
  background: #fff; border-radius: 1vh;
}
.status { margin-top: 4vh; font-size: 1.8vh; }
.message { color: var(--ink-muted); font-size: 2.6vh; }
"""

SCRIPT = """'use strict';
// Polls the kiosk for what to show, and opens the board once it loads.
const MESSAGES = {
  starting: 'Starting…',
  offline: 'Reconnecting to Riffle…',
  busy: 'Too many codes asked for. Trying again in a minute…',
};
let shownCode = null;

async function refresh() {
  let state;
  try {
    state = await (await fetch('/state', { cache: 'no-store' })).json();
  } catch (e) {
    state = { state: 'starting' };
  }
  if (state.state === 'ready') {
    location.replace(state.display_url);
    return;
  }
  const pairing = state.state === 'pairing';
  document.getElementById('pair').hidden = !pairing;
  document.getElementById('message').hidden = pairing;
  if (pairing && state.code !== shownCode) {
    shownCode = state.code;
    document.getElementById('code').textContent = state.code;
    document.getElementById('address').textContent = state.address;
    // Drawn on this Pi by qrencode from the server's link for this code.
    document.getElementById('qr').src = '/qr.svg?code=' + encodeURIComponent(state.code);
  }
  if (!pairing) {
    shownCode = null;
    document.getElementById('message').textContent = MESSAGES[state.state] || MESSAGES.starting;
  }
  setTimeout(refresh, 1000);
}

refresh();
"""


def make_handler(kiosk: Kiosk) -> type[BaseHTTPRequestHandler]:
    """Return a request handler class that serves ``kiosk``'s start page."""

    class Handler(BaseHTTPRequestHandler):
        """The start page, its stylesheet and script, and what it should show."""

        server_version = f"RiffleKiosk/{VERSION}"

        def do_GET(self) -> None:
            """Serve the start page and its parts."""
            path = self.path.split("?", 1)[0]
            if path == "/":
                kiosk.reload()
                self._send(PAGE.encode(), "text/html; charset=utf-8")
            elif path == "/kiosk.css":
                self._send(STYLE.encode(), "text/css; charset=utf-8")
            elif path == "/kiosk.js":
                self._send(SCRIPT.encode(), "text/javascript; charset=utf-8")
            elif path == "/qr.svg":
                self._send(kiosk.qr.encode(), "image/svg+xml")
            elif path == "/state":
                self._send(json.dumps(kiosk.state).encode(), "application/json")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def _send(self, body: bytes, content_type: str) -> None:
            """Send ``body`` with headers that keep it out of every cache."""
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            """Log requests at debug level, not to stderr."""
            logger.debug(format, *args)

    return Handler


# --- Commands ----------------------------------------------------------------


def restart_browser() -> None:
    """Close the browser's compositor; systemd starts it again on the start page."""
    pkill = shutil.which("pkill")
    if pkill is None:
        return
    subprocess.run(  # noqa: S603  # nosemgrep (fixed arguments)
        [pkill, "-x", "-u", str(os.getuid()), "cage"], check=False
    )


def serve(server: str, state_dir: Path) -> None:
    """Serve the start page on 127.0.0.1 and keep the kiosk's state up to date."""
    kiosk = Kiosk(Api(server), Store(state_dir), leave_board=restart_browser)
    threading.Thread(target=kiosk.run_forever, name="kiosk", daemon=True).start()
    httpd = ThreadingHTTPServer((HOST, PORT), make_handler(kiosk))
    logger.info("Riffle kiosk %s on http://%s:%d/ for %s", VERSION, HOST, PORT, server)
    httpd.serve_forever()


def status(server: str, state_dir: Path) -> int:
    """Log which display this Pi shows; return 1 if it isn't linked to one."""
    display = Store(state_dir).load()
    if display is None:
        logger.info("Not linked to a display: the TV shows a pairing code.")
        return 1
    logger.info("Linked to %s", display.display_name or "a display")
    logger.info("  %s", display.display_url)
    if Api(server).check(display.display_url) != "ok":
        logger.info("  but its board can't be loaded right now.")
    return 0


def unlink(state_dir: Path, restart: Callable[[], None]) -> int:
    """Forget the linked display and restart the browser, so the TV shows a new code."""
    Store(state_dir).clear()
    restart()
    logger.info("Unlinked. The TV now shows a new pairing code.")
    return 0


def restart_display() -> None:
    """Restart the kiosk's services (needs root), so the browser opens the start page."""
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return
    subprocess.run(  # noqa: S603  # nosemgrep (fixed arguments)
        [systemctl, "restart", "riffle-kiosk.service", "riffle-display.service"], check=False
    )


def main(argv: list[str] | None = None) -> int:
    """Run one of the commands; ``serve`` runs until the process is stopped."""
    parser = argparse.ArgumentParser(
        prog="riffle-kiosk", description="Riffle's Raspberry Pi kiosk."
    )
    parser.add_argument("command", choices=["serve", "status", "unlink"])
    args = parser.parse_args(argv)
    server = os.environ.get("RIFFLE_SERVER", DEFAULT_SERVER).rstrip("/")
    state_dir = Path(os.environ.get("RIFFLE_STATE_DIR", DEFAULT_STATE_DIR))
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    if args.command == "serve":
        serve(server, state_dir)
        return 0
    if args.command == "status":
        return status(server, state_dir)
    return unlink(state_dir, restart_display)


if __name__ == "__main__":
    sys.exit(main())

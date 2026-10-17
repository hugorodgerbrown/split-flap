# The TV polls a secret address

**Decision:** a TV opens its display at `/d/<uuid>/` with no sign-in, and
fetches `/d/<uuid>/state.json` every five seconds with `If-None-Match`.
The server answers 304 until a board's message changes.

**Why:** a TV's browser is a poor place to type an email code or use a
passkey, and the board is meant to be glanced at, so the display's uuid is
the secret (122 random bits). Anyone with the address can watch the board;
only its owner can change it, from the app or over MCP. Polling a small
JSON document works on every TV browser, survives the server restarting,
and needs nothing on Render beyond the web service. Websockets or
server-sent events would cut the delay but add a channel layer and
long-lived connections for a board that changes a few times a day.

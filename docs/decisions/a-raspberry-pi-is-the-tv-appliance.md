# A Raspberry Pi is the TV appliance

Status: accepted (2026-10-22)

## Context

Riffle should show on a Samsung TV (RAS-97). Samsung's TVs run Tizen, not
Android, so the Android TV app (docs/decisions/the-tv-app-is-a-shell-around-the-board.md)
can't go on them. The ways in were:

- **A Tizen app.** A second codebase, signed with the owner's own Samsung
  certificate and installed in Developer Mode.
- **A Fire TV Stick** (RAS-89) runs the Android TV app, but Amazon's newest
  sticks run Vega OS, which can't sideload apps, and every stick needs an
  Amazon account and pushes its services.
- **A Google TV stick** runs the app too, but needs a Google account and
  pushes subscriptions as well.
- **A Roku** has no browser engine, so the board would have to be redrawn
  in BrightScript: two boards to keep in step.
- **The TV's own browser** works, but has to be opened by hand each time and
  lets the screensaver in.

The owner wants a box with no accounts and no services on it.

## Decision

A Raspberry Pi running Raspberry Pi OS Lite is the TV appliance. One
script (`raspberry-pi/install.sh`) makes it boot straight into Chromium,
full screen under the `cage` kiosk compositor, on a start page served by
`raspberry-pi/riffle_kiosk.py`. That page is the Android app's native shell
again: it pairs by code with the same endpoints (`/d/pair/`), remembers the
link, checks the board loads, says "Reconnecting…" while it can't, and pairs
again if the display is deleted. Then it hands the browser to the board at
`/d/<uuid>/`, so the Pi, like the Android app, shows the real web board and
never redraws it.

## Consequences

- It works on any TV with HDMI, Samsung or not, and needs no account
  anywhere but Riffle.
- It costs more than a stick (about £60–70 for a Pi 4 kit) and needs a
  one-off setup over SSH; docs/raspberry-pi.md walks through it.
- With no remote, the Pi is managed over SSH: `riffle-kiosk status` and
  `sudo riffle-kiosk unlink`. Turning the TV on and off, or using the TV
  remote on the board, over HDMI-CEC is a later issue, as is a ready-made
  SD card image.
- The kiosk script must run on the Python Raspberry Pi OS ships (3.11+),
  with only the standard library; ruff and CI hold it to 3.11.
- The server didn't change: the TV pairing endpoints serve the Pi as they
  serve the Android app.

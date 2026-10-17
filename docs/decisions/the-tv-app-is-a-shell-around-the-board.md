# The TV app is a shell around the board

Status: accepted (2026-10-17)

## Context

People want Split-Flap as an app on their Android TV or Google TV, not as
a link typed into the TV's browser (RAS-67). The board (its flaps,
pictograms, colour tiles and polling) is the web page at `/d/<uuid>/`,
drawn by `board.css` and `splitflap.js`.

## Decision

`android-tv/` is a small Kotlin app with one activity. Until the TV is
linked it shows a pairing code (docs/decisions/a-tv-app-pairs-with-a-short-code.md);
after that it shows the display's own board page in a full-screen
WebView. The native layer only does what a TV's browser does badly: a
tile on the home screen, keeping the screen on, reloading by itself when
the page can't load, remembering the link, and (if asked) starting when
the TV turns on. It uses plain Android views and one library (ZXing, for
the QR code), so there is little to keep up to date.

## Consequences

- Every change to the board reaches TVs with no app update; the app
  changes only when its own job does.
- Redrawing the board natively was ruled out: two boards would drift. A
  Trusted Web Activity was ruled out: Google TV has no Chrome to host one.
- The WebView follows links only on our own server, and only opens a
  display link of the form `/d/<uuid>/` there.
- The remote's arrow keys go to the page. Reaching the board's control
  bar with them is the page's job (RAS-61), not the app's.
- The app is sideloaded (docs/android-tv.md); a Play Store listing is a
  later decision.
- Starting with the TV needs Android's "display over other apps"
  permission, which Google TV hides, so it is off by default and the
  app says how to allow it.

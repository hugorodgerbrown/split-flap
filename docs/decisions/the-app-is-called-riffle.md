# The app is called Riffle, and its marks are drawn from the board

Status: accepted (2026-10-17)

## Context

The app was generated as Split-Flap. That name describes the mechanism, so
no one can own it, and it reads as a category rather than a product (RAS-72).

## Decision

The app is called **Riffle**, after the way the flaps move, like a deck of
cards being riffled. The name was renamed through the template's answers
(`copier update --data project_name=Riffle`), so `.copier-answers.yml`
agrees with `apps/pwa/conf.py` and later template updates merge cleanly.
"Split-flap" stays as the word for the kind of display, and code names
(`split-flap` as the package and repo name, `splitflap.js`) are unchanged.

Every mark is one of the board's own tiles: an R in the flap font, split
across the hinge. `bin/shoot-icons` draws the app icons, favicons, the
header's wordmark (the tile beside the name) and the TV app's launcher icon
and banner as small pages and photographs them, so the type is the real
Barlow, not an approximation. It replaces the template's `bin/make-icons`
placeholder.

## Consequences

- The PNGs keep 128 colours, so the icon and the wordmark fit the offline
  shell's byte budget (`tests/test_performance.py`). The favicons aren't
  precached: a browser tab without its icon offline costs nothing.
- `tests/test_name.py` fails if "Split-Flap" comes back into a page, a
  script, an MCP tool or the TV app's strings.
- The Linear project keeps its name, Split-Flap.

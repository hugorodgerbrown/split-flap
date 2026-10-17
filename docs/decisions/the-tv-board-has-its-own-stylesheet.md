# The TV board has its own stylesheet

**Decision:** the split-flap board at `/d/<uuid>/` is styled by
`static/css/board.css` and drawn by `static/js/splitflap.js`, apart from
`app.css` and the design page.

**Why:** the board is the product, drawn as a physical object: charcoal
flaps lit from above, a split with axle notches, Vestaboard's seven tile
colours and cream ink. Its palette and measurements describe that object,
not the app's interface, and they would take most of DESIGN.md's colour
budget on their own. The page is standalone (it extends no base template
and loads no app script), so nothing in it can drift into the app.

**Still holds:** no inline script or style (the CSP applies), fonts are
self-hosted, the pictograms are masks painted with the board's ink, and
`splitflap.js` names no colour literals.

## The front page shows the same board (RAS-62)

The front page's hero is the real board, not a picture of it (DESIGN.md,
"The front page"), so `board.css` now holds only the board itself: its
palette, frame, flaps and tiles. The TV's page around it (the dark wall,
the full-screen stage, the control bar) moved to `static/css/tv.css`, which
only `tv.html` loads. `.board--fluid` sizes the board to its container
(`.board-fit`, a container query) instead of to the screen.

`apps/public/board.py` draws the first demo board on the server, so the
page reads the same without JavaScript, and `static/js/front_board.js`
flips through the rest. It repeats a few lines of `splitflap.js`'s flap
logic rather than sharing them: `splitflap.js` is one script for the TV,
being reshaped by RAS-60 and RAS-61. When the board page's live preview
(RAS-61) makes a third caller, pull the flap into one shared script.

## The board on the app's pages (RAS-61)

The display page and each board's page draw the same board, still rather
than flipping, as `.board--fluid` from `board.css` (the third caller RAS-62
expected). The design page doesn't show it, for the same reason the TV's
board isn't there; the board page's palette keys draw their tile with
`board.css`'s `.flap`, for the same reason.

- `static/js/flaptext.js` lays a message out on the tiles for both the TV
  and the app's pages, and `apps/boards/layout.py` mirrors it so the pages
  draw the board before any script runs. Both are held to the same sample
  messages in `tests/boards/layout_cases.json`. Nothing here flips, so the
  flap logic stays in `splitflap.js` and `front_board.js`.
- `static/img/pictograms.svg` draws the pictograms as `<use>` symbols
  (`.face__icon`), so a page without script still shows them: the TV's
  masks need a style set by script. It is made from flaptext.js's drawings,
  and `tests/js/test_flaptext.js` fails if the two differ.

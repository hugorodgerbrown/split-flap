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

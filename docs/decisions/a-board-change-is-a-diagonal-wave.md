# A board change is a diagonal wave, and no tile turns more than 8 flaps

Status: accepted (2026-10-17)

## Context

When the board changed message, every tile started within about 0.7 s of
the others and turned through the whole drum to its target. On a typical
change most of the board was mid-flip at once, with tiles stopped halfway
between old and new symbols, for about 4 s. The colours and pictograms
sit near the end of the drum, just before the blank. So any tile turning
to a blank, or to a letter from a letter after it, flashed through every
one of them. The board looked like noise rather than a message changing
(RAS-76).

## Decision

- Tiles start in a diagonal wave: each row sweeps left to right, and each
  row starts a beat after the row above (`waveDelay` in
  `static/js/flapmotion.js`). Hugo chose this over a single left-to-right
  sweep and over row by row, because it reads in the same order as the
  text.
- A tile turns at most 8 flaps (`SPIN_CAP`). When its target is further
  round the drum, its first flap goes straight to the start of the target's
  run-in, the drum's symbols just before it (`nextFlap`). On the way to text
  or a blank, the run-in leaves out the colours and pictograms.
- The TV's board and the front page's share both through a new script,
  `static/js/flapmotion.js`, so they move the same way. It sits apart from
  `flaptext.js` because that script is in the app's precached shell, which
  has a byte budget, and no page under `/app/` flips.

## Consequences

- A change has one clean front, with the old message readable ahead of it
  and the new one behind it, and it is over in about 2.4 s instead of 3.9 s.
- The board is no longer strictly mechanical: a real drum can't skip
  symbols. Nobody can tell, because every flap still looks like one flap.
  But a tile no longer shows the full riffle a real board does on a long
  turn, and on the way to text it skips the colours and pictograms.
- The fast-spin pace (half-length flaps while far from the target) has
  gone, because no tile is far from its target any more.

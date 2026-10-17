/*
 * static/js/flapmotion.js — how a board changes from one message to the next.
 *
 * Shared by the TV's board (splitflap.js) and the front page's
 * (front_board.js), so both move the same way; it reads the drum from
 * static/js/flaptext.js. Not in the app's precached shell: no page under
 * /app/ flips. How and why: docs/board-animation.md.
 */
(() => {
  const { DRUM, DRUM_POS } = self.FlapText;

  // A tile turns at most SPIN_CAP flaps to a new symbol. Its last flaps are the
  // drum's symbols just before the target; from further round, its first flap
  // goes straight to the first of them. On the way to a letter, digit, mark or
  // blank, the run-in leaves out the colours and pictograms, so a tile never
  // flashes them before settling on text. Each flap still looks like one flap.
  const SPIN_CAP = 8;
  const loud = sym => sym.length > 1;
  function runIn(target) {
    const path = [target];
    for (let i = DRUM_POS.get(target) - 1; path.length < SPIN_CAP; i--) {
      const sym = DRUM[(i + DRUM.length) % DRUM.length];
      if (loud(target) || !loud(sym)) path.unshift(sym);
    }
    return path;
  }
  // The symbol a tile on ``cur`` shows next on its way to ``target``.
  function nextFlap(cur, target) {
    const path = runIn(target);
    return path[path.indexOf(cur) + 1];
  }

  // A board change runs as a diagonal wave: each row sweeps left to right, a
  // beat behind the row above, so it starts top left and ends bottom right.
  // The milliseconds before the tile at (row, col) starts turning.
  const WAVE_COL_MS = 55, WAVE_ROW_MS = 150, WAVE_SCATTER_MS = 20;
  const waveDelay = (row, col) => col * WAVE_COL_MS + row * WAVE_ROW_MS + Math.random() * WAVE_SCATTER_MS;

  self.FlapMotion = { SPIN_CAP, nextFlap, waveDelay };
})();

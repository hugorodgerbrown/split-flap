/*
 * static/js/flapmotion.js — how the board moves: one flip, and a whole board
 * changing from one message to the next.
 *
 * Board draws the flap modules and flips them; the TV's board (splitflap.js)
 * and the staff tuning page (board_tuning.js) use it. The front page's board
 * (front_board.js) has its own lighter flip but shares nextFlap and
 * waveDelay, so it changes message the same way. Every number is in TUNING,
 * which the tuning page changes live. It reads the drum from
 * static/js/flaptext.js. Not in the app's precached shell: no page under /app/
 * flips offline. How and why: docs/board-animation.md.
 */
(() => {
  const { COLS, ROWS, DRUM, DRUM_POS, ICON_MASKS, parse } = self.FlapText;

  // Every number that shapes the motion. The tuning page changes these live;
  // what's committed here is what every board uses.
  const DEFAULTS = Object.freeze({
    colMs: 55,         // the wave: delay per column...
    rowMs: 150,        // ...and per row, so it runs top left to bottom right
    scatterMs: 20,     // up to this much at random on each tile's start
    spinCap: 8,        // most flaps a tile turns to reach a new symbol
    flapMs: 48,        // one flap's length, plus a random share of...
    flapSpreadMs: 20,  // ...this, fixed per tile, like a real board's motors
    topShare: 0.42,    // the share of a flap spent on the top leaf's fall
    bounceDeg: 11,     // how far the bottom leaf kicks back up as it lands
  });
  const TUNING = { ...DEFAULTS };

  // A tile turns at most TUNING.spinCap flaps to a new symbol. Its last flaps
  // are the drum's symbols just before the target; from further round, its
  // first flap goes straight to the first of them. On the way to a letter,
  // digit, mark or blank, the run-in leaves out the colours and pictograms, so
  // a tile never flashes them before settling on text. Each flap still looks
  // like one flap.
  const loud = sym => sym.length > 1;
  function runIn(target) {
    const path = [target];
    for (let i = DRUM_POS.get(target) - 1; path.length < TUNING.spinCap; i--) {
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
  const waveDelay = (row, col) =>
    col * TUNING.colMs + row * TUNING.rowMs + Math.random() * TUNING.scatterMs;

  // ---- One flap: the top leaf falls, then the bottom leaf drops and bounces ----
  const TOP_FALL = [
    { transform: 'rotateX(0deg)', filter: 'brightness(1)' },
    { transform: 'rotateX(-90deg)', filter: 'brightness(0.45)' },
  ];
  const bottomFall = () => [
    { transform: 'rotateX(90deg)', filter: 'brightness(0.5)', offset: 0, easing: 'cubic-bezier(.4,0,1,1)' },
    { transform: 'rotateX(0deg)', filter: 'brightness(1)', offset: 0.7, easing: 'ease-out' },
    { transform: `rotateX(${TUNING.bounceDeg}deg)`, filter: 'brightness(0.95)', offset: 0.84, easing: 'ease-in' },
    { transform: 'rotateX(0deg)', filter: 'brightness(1)', offset: 1 },
  ];

  function makeHalf(cls) {
    const el = document.createElement('div');
    el.className = cls;
    const face = document.createElement('span');
    face.className = 'face';
    el.appendChild(face);
    return el;
  }
  function setFace(half, sym) {
    const face = half.firstChild;
    if (sym[0] === '{') { face.textContent = ''; face.className = `face colour t-${sym[1]}`; face.style.removeProperty('--icon'); }
    else if (sym.length > 1) { face.textContent = ''; face.className = 'face icon'; face.style.setProperty('--icon', ICON_MASKS[sym.slice(1, -1)]); }
    else { face.textContent = sym; face.className = 'face'; face.style.removeProperty('--icon'); }
  }

  class Cell {
    constructor(board) {
      this.board = board;
      this.el = document.createElement('div');
      this.el.className = 'cell';
      this.sTop = makeHalf('half top');
      this.sBot = makeHalf('half bottom');
      this.lTop = makeHalf('leaf top');
      this.lBot = makeHalf('leaf bottom');
      this.el.append(this.sTop, this.sBot, this.lTop, this.lBot);
      this.cur = ' ';
      this.target = ' ';
      this.running = false;
      // Each module's motor runs at a slightly different speed, like the real thing.
      this.motor = Math.random();
      this.drawn = 0;
      [this.sTop, this.sBot, this.lTop, this.lBot].forEach(h => setFace(h, ' '));
    }
    set(sym, delay) {
      this.target = sym;
      if (this.running || this.cur === sym) return;
      this.running = true;
      this.start = setTimeout(() => this.run(), delay);
    }
    async run() {
      this.start = null;
      while (this.cur !== this.target) {
        if (this.board.still()) { this.snap(this.target); break; }
        await this.flip(nextFlap(this.cur, this.target));
      }
      this.running = false;
    }
    snap(sym) {
      this.drawn++;  // drop any flap still waiting to be drawn
      // Drop a start still waiting, so the next show() schedules it afresh.
      if (this.start) { clearTimeout(this.start); this.start = null; this.running = false; }
      this.a1?.cancel(); this.a2?.cancel();
      [this.sTop, this.sBot, this.lTop, this.lBot].forEach(h => setFace(h, sym));
      this.cur = sym;
    }
    // Fire-and-forget animations paced by a timer, so quick flaps are not held back by frame timing.
    // The clack is played on time and the flap drawn lagMs() later, so they're heard and seen together.
    flip(next) {
      const { clack, lagMs, speed } = this.board.hooks;
      const d = (TUNING.flapMs + this.motor * TUNING.flapSpreadMs) * speed();
      const top = TUNING.topShare;
      const prev = this.cur, drawn = this.drawn;
      const draw = () => {
        if (drawn !== this.drawn) return;
        this.a1?.cancel(); this.a2?.cancel();
        setFace(this.sTop, next);
        setFace(this.sBot, prev);
        setFace(this.lTop, prev);
        setFace(this.lBot, next);
        this.a1 = this.lTop.animate(TOP_FALL, { duration: d * top, easing: 'cubic-bezier(.55,0,1,.45)', fill: 'forwards' });
        this.a2 = this.lBot.animate(bottomFall(), { duration: d * (1 - top), delay: d * top, fill: 'both' });
      };
      const lag = lagMs();
      if (lag > 0) setTimeout(draw, lag); else draw();
      setTimeout(clack, d * 0.65);
      this.cur = next;
      return new Promise(r => setTimeout(r, d));
    }
  }

  // The 22x6 flap modules in ``grid``. Hooks: clack() plays one flap's sound,
  // lagMs() is how long after it to draw the flap, speed() multiplies every
  // length (a speed preset), and still() says to snap rather than flip.
  class Board {
    constructor(grid, hooks = {}) {
      this.hooks = { clack: () => {}, lagMs: () => 0, speed: () => 1, ...hooks };
      const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
      this.still = () => reduceMotion || document.hidden;
      this.shown = '';
      grid.style.setProperty('--cols', COLS);
      this.cells = Array.from({ length: COLS * ROWS }, () => new Cell(this));
      grid.append(...this.cells.map(c => c.el));
    }
    // Each of the board's rows as its tiles' symbols.
    static tiles(lines) {
      return Array.from({ length: ROWS }, (_, r) => {
        const syms = parse(lines[r] ?? '').slice(0, COLS);
        while (syms.length < COLS) syms.push(' ');
        return syms;
      });
    }
    // Turn the tiles to ``lines`` in the diagonal wave; tiles already showing them stay still.
    show(lines) {
      const rows = Board.tiles(lines);
      const key = rows.map(r => r.join('')).join('|');
      if (key === this.shown) return;
      this.shown = key;
      rows.forEach((syms, r) => syms.forEach((sym, c) => {
        this.cells[r * COLS + c].set(sym, waveDelay(r, c) * this.hooks.speed());
      }));
    }
    // Show ``lines`` at once, without flipping.
    snap(lines) {
      const rows = Board.tiles(lines);
      this.cells.forEach((cell, i) => { cell.target = rows[Math.floor(i / COLS)][i % COLS]; cell.snap(cell.target); });
      this.shown = rows.map(r => r.join('')).join('|');
    }
  }

  self.FlapMotion = { DEFAULTS, TUNING, nextFlap, waveDelay, Board };
})();

/*
 * static/js/front_board.js — flips the front page's board through its demo boards.
 *
 * The server draws the first board (apps/public/board.py), so the page reads
 * the same without this script. With it, the board opens blank and flips the
 * first board in, as the display does when it loads, then every few seconds
 * turns each tile through the drum to the next board's symbol, flap by flap
 * (as static/js/splitflap.js does). Reduced motion shows each board without
 * flipping. The sound toggle under the board turns on the flap sound
 * (static/js/flap_sound.js); it stays hidden without motion, as there's
 * nothing to hear.
 */
(() => {
  const board = document.querySelector('[data-front-board]');
  if (!board) return;
  const frames = JSON.parse(board.dataset.frames);
  const names = JSON.parse(board.dataset.names);
  const labels = JSON.parse(board.dataset.labels);
  const nameEl = board.querySelector('[data-board-name]');
  const leds = [...board.querySelectorAll('.led')];
  const HOLD_MS = 6500;
  const START_MS = 400;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // The drum's order, as splitflap.js turns through it (pictograms aside).
  const DRUM = [' ', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ', ...'1234567890', ...'!@#$()-+&=;:\'"%,./?°',
    '{r}', '{o}', '{y}', '{g}', '{b}', '{v}', '{w}'];
  const POS = new Map(DRUM.map((s, i) => [s, i]));

  function setFace(face, sym) {
    const tile = sym.length === 3;
    face.className = tile ? `face colour t-${sym[1]}` : 'face';
    face.textContent = tile ? '' : sym;
  }
  function leaf(cls, sym) {
    const el = document.createElement('div');
    el.className = `leaf ${cls}`;
    const face = document.createElement('span');
    el.append(face);
    setFace(face, sym);
    return el;
  }

  const TOP_FALL = [{ transform: 'rotateX(0deg)' }, { transform: 'rotateX(-90deg)' }];
  const BOTTOM_FALL = [{ transform: 'rotateX(90deg)' }, { transform: 'rotateX(0deg)' }];

  // The board opens blank and flips in its first message, as the display
  // does when it loads; without motion it keeps the message the server drew.
  const cells = [...board.querySelectorAll('.cell')].map((el, i) => {
    const sym = reduceMotion ? frames[0][i] : ' ';
    const lTop = leaf('top', sym);
    const lBot = leaf('bottom', sym);
    el.append(lTop, lBot);
    const [sTop, sBot] = el.querySelectorAll('.half');
    const faces = [sTop, sBot, lTop, lBot].map(h => h.firstElementChild);
    faces.forEach(f => setFace(f, sym));
    return { cur: sym, target: sym, running: false, faces, lTop, lBot, ms: 48 + Math.random() * 20 };
  });

  function snap(cell, sym) {
    cell.faces.forEach(f => setFace(f, sym));
    cell.cur = sym;
  }

  function flip(cell, next, pace) {
    const d = cell.ms * pace;
    const [sTop, sBot, lTop, lBot] = cell.faces;
    setFace(sTop, next);
    setFace(sBot, cell.cur);
    setFace(lTop, cell.cur);
    setFace(lBot, next);
    cell.lTop.animate(TOP_FALL, { duration: d * 0.45, easing: 'ease-in', fill: 'forwards' });
    cell.lBot.animate(BOTTOM_FALL, { duration: d * 0.55, delay: d * 0.45, easing: 'ease-out', fill: 'both' });
    setTimeout(() => window.FlapSound?.clack(), d * 0.65);
    cell.cur = next;
    // Once the leaves have landed, every face shows the new symbol, so the
    // old one (a cream tile, say) can't peep out from under a leaf's edge.
    return new Promise(r => setTimeout(() => {
      if (cell.cur === next) { setFace(sBot, next); setFace(lTop, next); }
      r();
    }, d));
  }

  async function run(cell) {
    cell.running = true;
    while (cell.cur !== cell.target) {
      if (reduceMotion || document.hidden || !POS.has(cell.target) || !POS.has(cell.cur)) {
        snap(cell, cell.target);
        break;
      }
      // Fast while far from the target, then settle for the last few flaps.
      const left = (POS.get(cell.target) - POS.get(cell.cur) + DRUM.length) % DRUM.length;
      await flip(cell, DRUM[(POS.get(cell.cur) + 1) % DRUM.length], left > 8 ? 0.5 : 1);
    }
    cell.running = false;
  }

  let shown = 0;
  function show(i) {
    shown = i;
    board.setAttribute('aria-label', labels[i]);
    nameEl.textContent = names[i];
    leds.forEach((led, j) => led.classList.toggle('on', j === i));
    cells.forEach((cell, k) => {
      cell.target = frames[i][k];
      if (cell.running || cell.cur === cell.target) return;
      // A left-to-right wave with a little scatter.
      const delay = (k % 22) * 32 + Math.floor(k / 22) * 14 + Math.random() * 70;
      setTimeout(() => run(cell), delay);
    });
  }

  const soundToggle = document.querySelector('[data-sound-toggle]');
  if (soundToggle && window.FlapSound && !reduceMotion) {
    soundToggle.hidden = false;
    soundToggle.addEventListener('click', () => {
      soundToggle.setAttribute('aria-pressed', window.FlapSound.toggle());
    });
  }

  setTimeout(() => show(0), START_MS);
  setInterval(() => { if (!document.hidden) show((shown + 1) % frames.length); }, HOLD_MS);
})();

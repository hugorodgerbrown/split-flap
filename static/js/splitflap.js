/*
 * static/js/splitflap.js — the split-flap board the TV shows (/d/<uuid>/).
 *
 * Draws a 22x6 grid of flap modules that turn through a fixed drum of
 * characters, colour tiles and pictograms to reach each new message. It
 * polls the display's state (data-state-url) and flips only the tiles that
 * change. Boards show only what they're given: an empty board shows its name.
 *
 * The flap sound follows the display page's setting (state.sound) whenever it
 * changes; the HUD's Sound button and the S key switch it for this screen
 * meanwhile. Browsers start sound only after a tap or key press, so until then
 * a sound that's on shows "Tap for sound".
 */
(() => {
  const { COLS, ROWS, ICONS, DRUM, DRUM_POS, parse, message } = self.FlapText;
  const CYCLE_MS = 30000;
  // Flip speed presets: each multiplies flap timing and the cascade delay.
  const SPEEDS = [{ name: 'Slow', k: 1.8 }, { name: 'Normal', k: 1 }, { name: 'Fast', k: 0.5 }];
  let speed = 1;
  try { const v = localStorage.getItem('splitflap.speed'); if (v !== null && SPEEDS[+v]) speed = +v; } catch (e) {}
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Each pictogram as a mask, painted in flap ink by board.css.
  const ICON_URL = Object.fromEntries(Object.entries(ICONS).map(([k, svg]) => [k,
    `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">${svg}</svg>`)}")`]));

  // ---- Boards: whatever the server says each one shows, filled by poll() ----
  const root = document.getElementById('board');
  let BOARDS = [];

  // A posted message, or the board's name while it has none.
  const renderBoard = b => message(b ? (b.message || b.name) : '');

  // ---- Flap cells ----
  const grid = document.getElementById('grid');
  grid.style.setProperty('--cols', COLS);

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
    else if (sym.length > 1) { face.textContent = ''; face.className = 'face icon'; face.style.setProperty('--icon', ICON_URL[sym.slice(1, -1)]); }
    else { face.textContent = sym; face.className = 'face'; face.style.removeProperty('--icon'); }
  }

  const TOP_FALL = [
    { transform: 'rotateX(0deg)', filter: 'brightness(1)' },
    { transform: 'rotateX(-90deg)', filter: 'brightness(0.45)' },
  ];
  const BOTTOM_FALL = [
    { transform: 'rotateX(90deg)', filter: 'brightness(0.5)', offset: 0, easing: 'cubic-bezier(.4,0,1,1)' },
    { transform: 'rotateX(0deg)', filter: 'brightness(1)', offset: 0.7, easing: 'ease-out' },
    { transform: 'rotateX(11deg)', filter: 'brightness(0.95)', offset: 0.84, easing: 'ease-in' },
    { transform: 'rotateX(0deg)', filter: 'brightness(1)', offset: 1 },
  ];

  class Cell {
    constructor() {
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
      this.ms = 48 + Math.random() * 20;
      [this.sTop, this.sBot, this.lTop, this.lBot].forEach(h => setFace(h, ' '));
    }
    set(sym, delay) {
      this.target = sym;
      if (this.running || this.cur === sym) return;
      this.running = true;
      setTimeout(() => this.run(), delay);
    }
    async run() {
      while (this.cur !== this.target) {
        if (reduceMotion || document.hidden) { this.snap(this.target); break; }
        // Spin fast while far from the target, then settle at normal speed for the last few flaps.
        const left = (DRUM_POS.get(this.target) - DRUM_POS.get(this.cur) + DRUM.length) % DRUM.length;
        await this.flip(DRUM[(DRUM_POS.get(this.cur) + 1) % DRUM.length], left > 10 ? 0.5 : 1);
      }
      this.running = false;
    }
    snap(sym) {
      this.a1?.cancel(); this.a2?.cancel();
      [this.sTop, this.sBot, this.lTop, this.lBot].forEach(h => setFace(h, sym));
      this.cur = sym;
    }
    // Fire-and-forget animations paced by a timer, so fast spins are not held back by frame timing.
    flip(next, pace = 1) {
      const d = this.ms * pace * SPEEDS[speed].k;
      this.a1?.cancel(); this.a2?.cancel();
      setFace(this.sTop, next);
      setFace(this.sBot, this.cur);
      setFace(this.lTop, this.cur);
      setFace(this.lBot, next);
      this.a1 = this.lTop.animate(TOP_FALL, { duration: d * 0.42, easing: 'cubic-bezier(.55,0,1,.45)', fill: 'forwards' });
      this.a2 = this.lBot.animate(BOTTOM_FALL, { duration: d * 0.58, delay: d * 0.42, fill: 'both' });
      setTimeout(() => sound.clack(), d * 0.65);
      this.cur = next;
      return new Promise(r => setTimeout(r, d));
    }
  }

  const cells = [];
  for (let i = 0; i < COLS * ROWS; i++) {
    const c = new Cell();
    cells.push(c);
    grid.appendChild(c.el);
  }

  let shown = '';
  function show(lines) {
    const rows = Array.from({ length: ROWS }, (_, r) => {
      const syms = parse(lines[r] ?? '').slice(0, COLS);
      while (syms.length < COLS) syms.push(' ');
      return syms;
    });
    const key = rows.map(r => r.join('')).join('|');
    if (key === shown) return;
    shown = key;
    rows.forEach((syms, r) => syms.forEach((sym, c) => {
      // A left-to-right wave with a little scatter.
      cells[r * COLS + c].set(sym, (c * 32 + r * 14 + Math.random() * 70) * SPEEDS[speed].k);
    }));
  }

  // ---- Sound: a short synthesised clack per flap, throttled into a rattle ----
  const sound = {
    on: false, ctx: null, bufs: [], last: 0,
    // Whether the browser is playing: it holds sound back until a tap or key press.
    running() { return this.ctx?.state === 'running'; },
    init() {
      if (this.ctx) return;
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      this.ctx = new Ctx();
      const sr = this.ctx.sampleRate;
      for (let v = 0; v < 4; v++) {
        const n = Math.floor(sr * 0.03);
        const buf = this.ctx.createBuffer(1, n, sr);
        const data = buf.getChannelData(0);
        const tone = 1500 + v * 260;
        for (let i = 0; i < n; i++) {
          const t = i / sr;
          data[i] = (Math.random() * 2 - 1) * Math.exp(-t * 380) * 0.7
            + Math.sin(2 * Math.PI * tone * t) * Math.exp(-t * 700) * 0.35
            + Math.sin(2 * Math.PI * 180 * t) * Math.exp(-t * 120) * 0.3;
        }
        this.bufs.push(buf);
      }
      this.out = this.ctx.createGain();
      this.out.gain.value = 0.5;
      const lp = this.ctx.createBiquadFilter();
      lp.type = 'lowpass'; lp.frequency.value = 6000;
      this.out.connect(lp).connect(this.ctx.destination);
    },
    clack() {
      if (!this.on || !this.ctx) return;
      const t = this.ctx.currentTime;
      if (t - this.last < 0.005) return;
      this.last = t;
      const src = this.ctx.createBufferSource();
      src.buffer = this.bufs[(Math.random() * this.bufs.length) | 0];
      src.playbackRate.value = 0.85 + Math.random() * 0.3;
      const g = this.ctx.createGain();
      g.gain.value = 0.08 + Math.random() * 0.08;
      src.connect(g).connect(this.out);
      src.start();
    },
  };

  // ---- Sizing: fit the board to the screen ----
  function fit() {
    const stage = document.querySelector('.stage');
    const cs = getComputedStyle(stage);
    const availW = stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const availH = stage.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    const R = { ch: 1.38, gx: 0.12, gy: 0.16, pad: 0.85 };
    const unitsW = COLS + (COLS - 1) * R.gx + 2 * R.pad;
    const unitsH = ROWS * R.ch + (ROWS - 1) * R.gy + R.pad * 2.6;
    const cw = Math.max(8, Math.min(availW / unitsW, (availH * 0.94) / unitsH));
    const s = document.documentElement.style;
    s.setProperty('--cw', cw + 'px');
    s.setProperty('--ch', cw * R.ch + 'px');
    s.setProperty('--gx', cw * R.gx + 'px');
    s.setProperty('--gy', cw * R.gy + 'px');
    s.setProperty('--pad', cw * R.pad + 'px');
    s.setProperty('--fs', cw * R.ch * 0.66 + 'px');
    s.setProperty('--r', Math.max(1, cw * 0.07) + 'px');
  }
  addEventListener('resize', fit);
  fit();

  // ---- Board switching ----
  const tabs = document.getElementById('tabs');
  const leds = document.getElementById('leds');
  const nameEl = document.getElementById('boardName');
  let active = 0, auto = true, lastSwitch = Date.now();

  // Rebuild the tabs and lights when the boards (or their names or order) change.
  function setBoards(boards) {
    const names = boards.map(b => b.name).join('\n');
    const changed = names !== BOARDS.map(b => b.name).join('\n');
    BOARDS = boards;
    if (!changed) return;
    tabs.replaceChildren();
    leds.replaceChildren();
    BOARDS.forEach((b, i) => {
      const btn = document.createElement('button');
      btn.type = 'button'; btn.role = 'tab'; btn.textContent = b.name;
      btn.addEventListener('click', () => select(i));
      tabs.appendChild(btn);
      const led = document.createElement('span');
      led.className = 'led';
      leds.appendChild(led);
    });
    select(Math.min(active, BOARDS.length - 1));
  }

  function select(i) {
    if (!BOARDS.length) return;
    active = (i + BOARDS.length) % BOARDS.length;
    lastSwitch = Date.now();
    [...tabs.children].forEach((t, j) => t.setAttribute('aria-selected', j === active));
    [...leds.children].forEach((l, j) => l.classList.toggle('on', j === active));
    nameEl.textContent = BOARDS[active].name;
    show(renderBoard(BOARDS[active]));
  }

  setInterval(() => {
    if (auto && Date.now() - lastSwitch > CYCLE_MS) select(active + 1);
    else show(renderBoard(BOARDS[active]));
  }, 1000);

  // ---- Controls ----
  const hud = document.getElementById('hud');
  const cycleBtn = document.getElementById('cycle');
  const soundBtn = document.getElementById('sound');
  const soundHint = document.getElementById('soundHint');

  function setAuto(v) { auto = v; lastSwitch = Date.now(); cycleBtn.setAttribute('aria-pressed', v); }
  const canPlay = Boolean(window.AudioContext || window.webkitAudioContext);
  function showSound() {
    soundBtn.setAttribute('aria-pressed', sound.on);
    soundHint.hidden = !sound.on || sound.running() || !canPlay;
  }
  // Try to start the sound; most browsers let it start only from a tap or key press.
  function startSound() {
    if (!sound.on || sound.running()) return;
    sound.init();
    if (!sound.ctx) return;
    sound.ctx.onstatechange = showSound;
    sound.ctx.resume?.().catch(() => {});
  }
  function setSound(on) {
    sound.on = on;
    showSound();
    startSound();
  }
  function toggleSound() {
    // A press while the sound waits for one starts it, rather than turning it off.
    if (sound.on && !sound.running()) startSound();
    else setSound(!sound.on);
  }
  function toggleFs() {
    try {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen?.().catch(() => {});
    } catch (e) {}
  }

  const speedGroup = document.getElementById('speed');
  SPEEDS.forEach((sp, i) => {
    const btn = document.createElement('button');
    btn.type = 'button'; btn.textContent = sp.name;
    btn.addEventListener('click', () => setSpeed(i));
    speedGroup.appendChild(btn);
  });
  function setSpeed(i) {
    speed = Math.max(0, Math.min(SPEEDS.length - 1, i));
    [...speedGroup.children].forEach((b, j) => {
      b.setAttribute('aria-pressed', j === speed);
    });
    try { localStorage.setItem('splitflap.speed', speed); } catch (e) {}
  }
  setSpeed(speed);

  cycleBtn.addEventListener('click', () => setAuto(!auto));
  soundBtn.addEventListener('click', toggleSound);
  document.getElementById('fs').addEventListener('click', toggleFs);

  // Any tap or key press starts a sound that's waiting, except the Sound button and S,
  // which do it themselves.
  const soundKey = e => e.target.closest?.('#sound') || (e.type === 'keydown' && e.key.toLowerCase() === 's');
  ['pointerdown', 'keydown'].forEach(ev => addEventListener(ev, e => { if (!soundKey(e)) startSound(); }, { capture: true }));

  addEventListener('keydown', e => {
    poke();
    if (e.target.closest?.('button') && (e.key === 'Enter' || e.key === ' ')) return;
    const k = e.key.toLowerCase();
    if (k === 'arrowright') select(active + 1);
    else if (k === 'arrowleft') select(active - 1);
    else if (/^[1-9]$/.test(k) && +k <= BOARDS.length) select(+k - 1);
    else if (k === ' ') { e.preventDefault(); setAuto(!auto); }
    else if (k === 's') toggleSound();
    else if (k === '-' || k === '_') setSpeed(speed - 1);
    else if (k === '=' || k === '+') setSpeed(speed + 1);
    else if (k === 'f') toggleFs();
  });

  // Hide the controls and cursor when nobody is touching anything.
  let idleTimer;
  function poke() {
    document.body.classList.remove('idle');
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => document.body.classList.add('idle'), 3500);
  }
  ['mousemove', 'pointerdown', 'touchstart'].forEach(ev => addEventListener(ev, poke, { passive: true }));
  poke();

  // Keep the TV awake while the board is showing.
  let lock = null;
  async function wake() {
    try { if (!lock && navigator.wakeLock) { lock = await navigator.wakeLock.request('screen'); lock.addEventListener('release', () => { lock = null; }); } } catch (e) {}
  }
  addEventListener('pointerdown', wake, { once: true });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) wake(); });

  // ---- Live content: ask the server what each board shows ----
  let etag = null;
  let lastPosted = null;  // newest posted_at seen; null until the first answer
  // The display page's sound setting, as last seen. The page carries it, so a tap
  // before the first poll still starts the sound.
  let soundSetting = root.dataset.sound === 'on';
  setSound(soundSetting);
  async function poll() {
    try {
      const response = await fetch(root.dataset.stateUrl, {
        headers: etag ? { 'If-None-Match': etag } : {},
        cache: 'no-cache',
      });
      if (response.status === 200) {
        etag = response.headers.get('ETag');
        const state = await response.json();
        setBoards(state.boards);
        if (Boolean(state.sound) !== soundSetting) {
          soundSetting = Boolean(state.sound);
          setSound(soundSetting);
        }
        const newest = state.boards.reduce((a, b) => ((b.posted_at || '') > (a.posted_at || '') ? b : a), {});
        // Something new was posted since we last looked: turn to that board so it's seen.
        if (lastPosted !== null && newest.posted_at && newest.posted_at > lastPosted) {
          select(state.boards.indexOf(newest));
        }
        lastPosted = newest.posted_at || '';
        show(renderBoard(BOARDS[active]));
      }
    } catch (e) {
      // Offline, or the server is restarting: keep showing what we have.
    }
    setTimeout(poll, (+root.dataset.pollSeconds || 5) * 1000);
  }

  const start = () => setTimeout(poll, 400);
  (document.fonts?.ready || Promise.resolve()).then(start, start);
})();

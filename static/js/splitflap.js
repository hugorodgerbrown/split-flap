/*
 * static/js/splitflap.js — the split-flap board the TV shows (/d/<uuid>/).
 *
 * Draws a 22x6 grid of flap modules that turn through a fixed drum of
 * characters, colour tiles and pictograms to reach each new message. It
 * polls the display's state (data-state-url) and flips only the tiles that
 * change. Boards show only what they're given: an empty board shows its name.
 */
(() => {
  const COLS = 22, ROWS = 6;
  const CYCLE_MS = 30000;
  // Flip speed presets: each multiplies flap timing and the cascade delay.
  const SPEEDS = [{ name: 'Slow', k: 1.8 }, { name: 'Normal', k: 1 }, { name: 'Fast', k: 0.5 }];
  let speed = 1;
  try { const v = localStorage.getItem('splitflap.speed'); if (v !== null && SPEEDS[+v]) speed = +v; } catch (e) {}
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // The drum: every symbol a flap can show, in the order it turns through them.
  // Pictograms printed in flap ink. Each is a 24x24 line drawing used as a mask.
  const CLOUD = 'M7 14h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.1 7 3.5 3.5 0 0 0 7 14z';
  const ICONS = {
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/>',
    cloud: '<path d="M7 18h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.1 11 3.5 3.5 0 0 0 7 18z"/>',
    partcloud: '<path d="M8.5 3v1.5M3 8.5h1.5M4.6 4.6l1 1M12.4 4.6l-1 1"/><path d="M5.6 11.2a3.5 3.5 0 1 1 6.3-2.9"/><path d="M9 20h8a3.5 3.5 0 0 0 .4-6.98A5 5 0 0 0 8.2 14 3 3 0 0 0 9 20z"/>',
    rain: `<path d="${CLOUD}"/><path d="M8 17l-1 3.5M12 17l-1 3.5M16 17l-1 3.5"/>`,
    storm: `<path d="${CLOUD}"/><path d="M12.5 15l-2.5 3.5h4L11.5 22"/>`,
    snow: '<path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9M9.5 4.5L12 6l2.5-1.5M9.5 19.5L12 18l2.5 1.5"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    umbrella: '<path d="M12 3a9 9 0 0 1 9 9H3a9 9 0 0 1 9-9z"/><path d="M12 12v7a2 2 0 0 0 4 0"/>',
    train: '<rect x="6" y="3" width="12" height="14" rx="3"/><path d="M6 10h12M9 13.5h.01M15 13.5h.01M9 17l-2 4M15 17l2 4"/>',
    plane: '<path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z" fill="black" stroke="none"/>',
    car: '<path d="M5 17h14v-5l-2-5H7l-2 5v5zM5 12h14"/><circle cx="8" cy="17" r="1.6"/><circle cx="16" cy="17" r="1.6"/>',
    bike: '<circle cx="6" cy="16" r="3.5"/><circle cx="18" cy="16" r="3.5"/><path d="M6 16l4-7h5l3 7M10 9l2 7h6M13.5 6H16"/>',
    home: '<path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/>',
    coffee: '<path d="M5 9h11v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V9zM16 11h1.5a2.5 2.5 0 0 1 0 5H16M8 3.5v2.5M11 3.5v2.5M14 3.5v2.5"/>',
    music: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    news: '<rect x="4" y="5" width="16" height="14" rx="1.5"/><path d="M7.5 9h9M7.5 12h9M7.5 15h5"/>',
    heart: '<path d="M12 20s-7.5-4.6-7.5-10.2A4.2 4.2 0 0 1 12 7.3a4.2 4.2 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z" fill="black"/>',
    star: '<path d="M12 3l2.6 6 6.4.3-5 4.1 1.8 6.6-5.8-3.7-5.8 3.7L8 13.4 3 9.3 9.4 9z" fill="black"/>',
    smile: '<circle cx="12" cy="12" r="9"/><path d="M8 14a4.6 4.6 0 0 0 8 0"/><circle cx="9" cy="9.8" r=".9" fill="black"/><circle cx="15" cy="9.8" r=".9" fill="black"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    cross: '<path d="M6 6l12 12M18 6L6 18"/>',
    up: '<path d="M12 20V4M6 10l6-6 6 6"/>',
    down: '<path d="M12 4v16M6 14l6 6 6-6"/>',
    left: '<path d="M20 12H4M10 6l-6 6 6 6"/>',
    right: '<path d="M4 12h16M14 6l6 6-6 6"/>',
  };
  const ICON_URL = Object.fromEntries(Object.entries(ICONS).map(([k, svg]) => [k,
    `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">${svg}</svg>`)}")`]));
  // Emoji people type, mapped onto the pictograms above.
  const EMOJI = {
    '☀': 'sun', '🌞': 'sun', '☁': 'cloud', '⛅': 'partcloud', '🌤': 'partcloud', '🌥': 'partcloud',
    '🌧': 'rain', '🌦': 'rain', '⛈': 'storm', '⚡': 'storm', '🌩': 'storm', '❄': 'snow', '🌨': 'snow',
    '🌙': 'moon', '🌛': 'moon', '☂': 'umbrella', '☔': 'umbrella',
    '🚆': 'train', '🚂': 'train', '🚄': 'train', '🚇': 'train', '🚉': 'train', '✈': 'plane', '🛫': 'plane',
    '🚗': 'car', '🚕': 'car', '🚲': 'bike', '🏠': 'home', '🏡': 'home', '☕': 'coffee',
    '🎵': 'music', '🎶': 'music', '♪': 'music', '♫': 'music', '📰': 'news',
    '❤': 'heart', '♥': 'heart', '💛': 'heart', '💙': 'heart', '💚': 'heart', '🧡': 'heart', '💜': 'heart',
    '★': 'star', '⭐': 'star', '🌟': 'star', '😀': 'smile', '😃': 'smile', '😊': 'smile', '🙂': 'smile', '😄': 'smile',
    '✓': 'check', '✔': 'check', '✅': 'check', '✗': 'cross', '✘': 'cross', '❌': 'cross',
    '↑': 'up', '⬆': 'up', '↓': 'down', '⬇': 'down', '←': 'left', '⬅': 'left', '→': 'right', '➡': 'right',
  };

  const DRUM = [' ', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ', ...'1234567890', ...'!@#$()-+&=;:\'"%,./?°',
    '{r}', '{o}', '{y}', '{g}', '{b}', '{v}', '{w}', ...Object.keys(ICONS).map(k => `:${k}:`)];
  const DRUM_POS = new Map(DRUM.map((s, i) => [s, i]));
  const ALIASES = { '’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-', '…': '.' };

  function parse(str) {
    const out = [];
    for (const m of String(str).matchAll(/\{([roygbvw])\}|:([a-z]+):|\p{Extended_Pictographic}\uFE0F?|[\s\S]/giu)) {
      if (m[1]) { out.push(`{${m[1].toLowerCase()}}`); continue; }
      const icon = m[2] ? (ICONS[m[2].toLowerCase()] && m[2].toLowerCase()) : EMOJI[m[0].replace('\uFE0F', '')];
      if (icon) { out.push(`:${icon}:`); continue; }
      if (m[2]) { out.push(':', ...parse(m[0].slice(1))); continue; }  // not a known name: show it as typed
      let ch = ALIASES[m[0]] || m[0].toUpperCase();
      if (ch === '\n') ch = ' ';
      out.push(DRUM_POS.has(ch) ? ch : ' ');
    }
    return out;
  }
  const len = s => parse(s).length;
  const pad = n => ' '.repeat(Math.max(0, n));
  const center = s => pad(Math.floor((COLS - len(s)) / 2)) + s;
  function wrap(text, width = COLS) {
    const lines = [];
    for (const para of String(text).split(/\n/)) {
      let line = '';
      for (const word of para.split(/\s+/).filter(Boolean)) {
        const next = line ? line + ' ' + word : word;
        if (len(next) <= width) { line = next; continue; }
        if (line) lines.push(line);
        line = word;
        while (len(line) > width) { lines.push(parse(line).slice(0, width).join('')); line = parse(line).slice(width).join(''); }
      }
      lines.push(line);
    }
    return lines;
  }
  function message(text) {
    const lines = wrap(text).slice(0, ROWS);
    const top = Math.floor((ROWS - lines.length) / 2);
    return Array.from({ length: ROWS }, (_, r) => center(lines[r - top] ?? ''));
  }

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
    if (sym[0] === '{') { face.textContent = ''; face.className = `face tile t-${sym[1]}`; face.style.removeProperty('--icon'); }
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

  function setAuto(v) { auto = v; lastSwitch = Date.now(); cycleBtn.setAttribute('aria-pressed', v); }
  function toggleSound() {
    sound.init();
    sound.ctx?.resume?.();
    sound.on = !sound.on;
    soundBtn.setAttribute('aria-pressed', sound.on);
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

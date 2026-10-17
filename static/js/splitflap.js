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
 *
 * A clack is heard a little after it's played (the browser's audio buffer, then
 * any soundbar), and a flap lasts about 50 ms, so while the sound plays each flap
 * is drawn that much later than its clack is played: the delay the browser
 * reports plus the display's Sound timing (state.sound_delay_ms). The display
 * page's Replay button (state.replays) flips the board again from blank.
 */
(() => {
  const { COLS, ROWS, message } = self.FlapText;
  const { Board } = self.FlapMotion;
  const CYCLE_MS = 30000;
  // Flip speed presets: each multiplies flap timing and the cascade delay.
  const SPEEDS = [{ name: 'Slow', k: 1.8 }, { name: 'Normal', k: 1 }, { name: 'Fast', k: 0.5 }];
  let speed = 1;
  try { const v = localStorage.getItem('splitflap.speed'); if (v !== null && SPEEDS[+v]) speed = +v; } catch (e) {}


  // ---- Boards: whatever the server says each one shows, filled by poll() ----
  const root = document.getElementById('board');
  let BOARDS = [];

  // A posted message, or the board's name while it has none.
  const renderBoard = b => message(b ? (b.message || b.name) : '');

  // ---- Flap cells (static/js/flapmotion.js) ----
  const board = new Board(document.getElementById('grid'), {
    clack: () => sound.clack(),
    lagMs: () => sound.lagMs(),
    speed: () => SPEEDS[speed].k,
  });
  const show = lines => board.show(lines);
  // Flip every tile again from blank, as if the message had just arrived.
  function replay() {
    board.snap([]);
    show(renderBoard(BOARDS[active]));
  }

  // ---- Sound: a short synthesised clack per flap, throttled into a rattle ----
  const sound = {
    on: false, ctx: null, bufs: [], last: 0,
    // The display's Sound timing: extra delay, in ms, for what the browser can't see (a soundbar).
    delayMs: 0,
    // Whether the browser is playing: it holds sound back until a tap or key press.
    running() { return this.ctx?.state === 'running'; },
    // How long after its clack is played to draw a flap: none while nothing plays.
    lagMs() {
      if (!this.on || !this.running()) return 0;
      const reported = ((this.ctx.outputLatency || 0) + (this.ctx.baseLatency || 0)) * 1000;
      return Math.round(reported + this.delayMs);
    },
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
  sound.delayMs = +root.dataset.soundDelay || 0;
  let replays = root.dataset.replays ?? null;
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
        sound.delayMs = +state.sound_delay_ms || 0;
        const newest = state.boards.reduce((a, b) => ((b.posted_at || '') > (a.posted_at || '') ? b : a), {});
        // Something new was posted since we last looked: turn to that board so it's seen.
        if (lastPosted !== null && newest.posted_at && newest.posted_at > lastPosted) {
          select(state.boards.indexOf(newest));
        }
        lastPosted = newest.posted_at || '';
        // Replay pressed on the display page since the page was drawn.
        const replayed = replays !== null && String(state.replays) !== replays;
        replays = String(state.replays);
        if (replayed) replay();
        else show(renderBoard(BOARDS[active]));
      }
    } catch (e) {
      // Offline, or the server is restarting: keep showing what we have.
    }
    setTimeout(poll, (+root.dataset.pollSeconds || 5) * 1000);
  }

  const start = () => setTimeout(poll, 400);
  (document.fonts?.ready || Promise.resolve()).then(start, start);
})();

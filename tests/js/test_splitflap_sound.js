// Tests for static/js/splitflap.js: the TV's flap sound following the display page's
// setting, starting at the first tap or key press as browsers require, the flaps
// held back so they land with their clacks, and the display page's Replay.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import '../../static/js/flaptext.js';
import '../../static/js/flapmotion.js';

// The TV's page, as the server draws it with the sound setting ``sound``.
const page = (sound, attrs = '') => `
  <div class="stage">
    <div class="board" id="board" data-state-url="/d/x/state/" data-poll-seconds="5" data-sound="${sound ? 'on' : 'off'}" ${attrs}>
      <div class="grid" id="grid"></div>
      <div class="engrave"><span id="boardName"></span><span id="leds"></span></div>
    </div>
  </div>
  <p id="soundHint" hidden>Tap for sound</p>
  <div id="hud">
    <div id="tabs"></div><div id="speed"></div>
    <button id="cycle" type="button" aria-pressed="true">Auto-cycle</button>
    <button id="sound" type="button" aria-pressed="false">Sound</button>
    <button id="fs" type="button">Full screen</button>
  </div>`;

// An AudioContext that, like a browser's, stays suspended until resumed from a gesture.
class FakeAudioContext {
  constructor() {
    this.state = 'suspended';
    this.sampleRate = 8000;
    this.baseLatency = 0.01;
    this.outputLatency = 0.04;
    FakeAudioContext.made.push(this);
  }
  createBuffer(channels, length) { return { getChannelData: () => new Float32Array(length) }; }
  createGain() { return { gain: { value: 1 }, connect: (next) => next }; }
  createBiquadFilter() { return { frequency: {}, connect: (next) => next }; }
  createBufferSource() { return { playbackRate: {}, connect: (next) => next, start() { FakeAudioContext.clacks.push(Date.now()); } }; }
  get destination() { return {}; }
  get currentTime() { return Date.now() / 1000; }
  resume() {
    if (FakeAudioContext.allowed) {
      this.state = 'running';
      this.onstatechange?.();
    }
    return Promise.resolve();
  }
}

let state;

async function load(sound, { polled = true, motion = false, attrs = '', delay = 0 } = {}) {
  state = { sound, sound_delay_ms: delay, replays: 0, boards: [{ name: 'Home', message: '', posted_at: null }] };
  document.body.innerHTML = page(sound, attrs);
  vi.useFakeTimers();
  vi.stubGlobal('matchMedia', () => ({ matches: !motion }));  // reduced motion: tiles snap
  vi.stubGlobal('fetch', vi.fn(async () => ({
    status: 200,
    headers: { get: () => null },
    json: async () => state,
  })));
  window.AudioContext = FakeAudioContext;
  vi.resetModules();
  await import('../../static/js/splitflap.js');
  if (polled) await poll();
}

// Let the TV ask the server what to show, and act on the answer.
async function poll() {
  await vi.advanceTimersByTimeAsync(5000);
}

const hint = () => document.getElementById('soundHint');
const button = () => document.getElementById('sound');
const press = (key) => window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
const tap = () => document.getElementById('board').dispatchEvent(new Event('pointerdown', { bubbles: true }));

beforeEach(() => {
  FakeAudioContext.clacks = [];
  FakeAudioContext.made = [];
  FakeAudioContext.allowed = false;
});

afterEach(() => {
  document.body.innerHTML = '';
  delete window.AudioContext;
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('the sound setting', () => {
  it('stays quiet, with no hint, while the setting is off', async () => {
    await load(false);
    expect(button().getAttribute('aria-pressed')).toBe('false');
    expect(hint().hidden).toBe(true);
    tap();
    expect(FakeAudioContext.made).toHaveLength(0);
  });

  it('asks for a tap when the setting is on, and starts the sound at the first one', async () => {
    await load(true);
    expect(button().getAttribute('aria-pressed')).toBe('true');
    expect(hint().hidden).toBe(false);
    FakeAudioContext.allowed = true;
    tap();
    expect(FakeAudioContext.made.at(-1).state).toBe('running');
    expect(hint().hidden).toBe(true);
  });

  it('starts the sound at a tap that comes before the first poll', async () => {
    await load(true, { polled: false });
    expect(hint().hidden).toBe(false);
    FakeAudioContext.allowed = true;
    tap();
    expect(FakeAudioContext.made.at(-1).state).toBe('running');
    expect(hint().hidden).toBe(true);
  });

  it('starts the sound at a key press too, as from a TV remote', async () => {
    await load(true);
    FakeAudioContext.allowed = true;
    press('ArrowRight');
    expect(hint().hidden).toBe(true);
  });

  it('plays straight away where the browser allows it', async () => {
    FakeAudioContext.allowed = true;
    await load(true);
    expect(hint().hidden).toBe(true);
    expect(button().getAttribute('aria-pressed')).toBe('true');
  });

  it('follows the setting when it changes on the display page', async () => {
    await load(false);
    state = { ...state, sound: true };
    await poll();
    expect(button().getAttribute('aria-pressed')).toBe('true');
    expect(hint().hidden).toBe(false);
    state = { ...state, sound: false };
    await poll();
    expect(button().getAttribute('aria-pressed')).toBe('false');
    expect(hint().hidden).toBe(true);
  });

  it('lets this screen switch it, until the setting next changes', async () => {
    FakeAudioContext.allowed = true;
    await load(true);
    button().click();
    expect(button().getAttribute('aria-pressed')).toBe('false');
    await poll();
    expect(button().getAttribute('aria-pressed')).toBe('false');
    state = { ...state, sound: false };
    await poll();
    state = { ...state, sound: true };
    await poll();
    expect(button().getAttribute('aria-pressed')).toBe('true');
  });

  it('starts a waiting sound when S is pressed, rather than turning it off', async () => {
    await load(true);
    FakeAudioContext.allowed = true;
    press('s');
    expect(button().getAttribute('aria-pressed')).toBe('true');
    expect(hint().hidden).toBe(true);
    press('s');
    expect(button().getAttribute('aria-pressed')).toBe('false');
  });

  it('shows no hint in a browser that has no sound', async () => {
    await load(false);
    delete window.AudioContext;
    vi.resetModules();
    document.body.innerHTML = page(false);
    await import('../../static/js/splitflap.js');
    state = { ...state, sound: true };
    await poll();
    expect(hint().hidden).toBe(true);
  });
});

describe('the flaps and their clacks', () => {
  // When each flap is drawn: the moment its falling leaf starts to animate.
  let drawn;
  beforeEach(() => {
    drawn = [];
    Element.prototype.animate = function animate() { drawn.push(Date.now()); return { cancel() {} }; };
  });
  afterEach(() => { delete Element.prototype.animate; });

  // Post ``message`` to the board and let every tile settle.
  async function post(message) {
    state = { ...state, boards: [{ name: 'Home', message, posted_at: null }] };
    await poll();
    await vi.advanceTimersByTimeAsync(5000);
  }

  // How long after the first clack the first flap is drawn.
  const gap = () => Math.min(...drawn) - Math.min(...FakeAudioContext.clacks);

  it('draws each flap at once while the sound is off', async () => {
    await load(false, { motion: true });
    await post('A');
    expect(drawn.length).toBeGreaterThan(0);
    expect(FakeAudioContext.clacks).toHaveLength(0);
  });

  it('holds the flaps back by the delay the browser reports, plus the Sound timing', async () => {
    FakeAudioContext.allowed = true;
    await load(true, { motion: true, attrs: 'data-sound-delay="150"', delay: 150 });
    await post('A');
    // The clack plays about two-thirds into its flap; the flap is drawn 50 + 150 ms after it starts.
    expect(gap()).toBeGreaterThan(150);
    expect(gap()).toBeLessThanOrEqual(200);
  });

  it('follows a new Sound timing from the display page', async () => {
    FakeAudioContext.allowed = true;
    await load(true, { motion: true });
    await vi.advanceTimersByTimeAsync(5000);
    drawn = [];
    FakeAudioContext.clacks = [];
    state = { ...state, sound_delay_ms: 400 };
    await post('A');
    expect(gap()).toBeGreaterThan(400);
  });

  it('flips the board again when Replay is pressed, and not otherwise', async () => {
    await load(false, { motion: true, attrs: 'data-replays="0"' });
    await post('HELLO');
    const settled = drawn.length;
    await poll();
    expect(drawn.length).toBe(settled);
    state = { ...state, replays: 1 };
    await poll();
    await vi.advanceTimersByTimeAsync(5000);
    expect(drawn.length).toBeGreaterThan(settled);
  });
});

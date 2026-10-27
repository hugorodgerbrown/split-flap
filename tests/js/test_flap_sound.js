// Tests for static/js/flap_sound.js: the flap sound is off until it is turned on,
// and plays through an iPhone's or iPad's silent mode.
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';

const started = vi.fn();

class FakeContext {
  constructor() { this.sampleRate = 8000; this.currentTime = 0; this.destination = {}; }
  resume() {}
  createBuffer(channels, length) { const data = new Float32Array(length); return { getChannelData: () => data }; }
  createGain() { return { gain: { value: 0 }, connect: node => node }; }
  createBiquadFilter() { return { frequency: { value: 0 }, connect: node => node }; }
  createBufferSource() { return { playbackRate: { value: 1 }, connect: node => node, start: started }; }
}

beforeAll(async () => {
  vi.stubGlobal('AudioContext', FakeContext);
  await import('../../static/js/flap_sound.js');
});

afterAll(() => {
  delete window.FlapSound;
  vi.unstubAllGlobals();
});

describe('flap sound', () => {
  it('is silent until it is turned on', () => {
    window.FlapSound.clack();
    expect(started).not.toHaveBeenCalled();
  });

  it('clacks once on, and stops when turned off', () => {
    expect(window.FlapSound.toggle()).toBe(true);
    window.FlapSound.ctx.currentTime = 1;
    window.FlapSound.clack();
    expect(started).toHaveBeenCalledTimes(1);
    expect(window.FlapSound.toggle()).toBe(false);
    window.FlapSound.ctx.currentTime = 1.5;
    window.FlapSound.clack();
    expect(started).toHaveBeenCalledTimes(1);
  });

  it('thins flaps that fall at the same moment into one clack', () => {
    window.FlapSound.toggle();
    window.FlapSound.ctx.currentTime = 2;
    const before = started.mock.calls.length;
    window.FlapSound.clack();
    window.FlapSound.clack();
    expect(started.mock.calls.length - before).toBe(1);
  });

  it('plays whatever the toggle says, for a page that keeps its own setting', () => {
    window.FlapSound.on = false;
    window.FlapSound.ctx.currentTime = 3;
    const before = started.mock.calls.length;
    window.FlapSound.play();
    expect(started.mock.calls.length - before).toBe(1);
  });

  it('asks Safari for the playback session when readied, so silent mode does not mute it', () => {
    Object.defineProperty(navigator, 'audioSession', { value: { type: 'auto' }, configurable: true });
    window.FlapSound.unlock();
    expect(navigator.audioSession.type).toBe('playback');
    delete navigator.audioSession;
  });
});

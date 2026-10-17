// Tests for static/js/front_board.js with motion: the board opens blank and flips its first board in.
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';

const cell = sym => `<div class="cell"><div class="half top"><span class="face">${sym}</span></div><div class="half bottom"><span class="face">${sym}</span></div></div>`;

beforeAll(async () => {
  vi.useFakeTimers();
  vi.stubGlobal('matchMedia', () => ({ matches: false }));
  // jsdom has no Web Animations; the flaps' timing runs on timers anyway.
  Element.prototype.animate = vi.fn();
  // The flap sound (static/js/flap_sound.js), off until the toggle is tapped.
  let on = false;
  vi.stubGlobal('FlapSound', { clack: vi.fn(), toggle: vi.fn(() => (on = !on)) });
  document.body.innerHTML = `
    <button type="button" aria-pressed="false" data-sound-toggle hidden>Sound</button>
    <div class="board" role="img" aria-label="Hi" data-front-board
         data-frames='[["H","I","{r}"],["Y","O","{g}"]]' data-names='["Morning","Weather"]' data-labels='["Hi","Yo"]'>
      <div class="grid">${cell('H')}${cell('I')}${cell('')}</div>
      <div class="engrave"><span data-board-name>Morning</span><span class="leds"><span class="led on"></span><span class="led"></span></span></div>
    </div>`;
  await import('../../static/js/flaptext.js');
  await import('../../static/js/front_board.js');
});

afterAll(() => {
  document.body.innerHTML = '';
  delete Element.prototype.animate;
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const tops = () => [...document.querySelectorAll('.cell .half.top .face')].map(f => f.className + '|' + f.textContent);

describe('front board launch', () => {
  it('opens blank, over the message the server drew', () => {
    expect(tops()).toEqual(['face| ', 'face| ', 'face| ']);
  });

  it('flips the first board in, flap by flap', async () => {
    await vi.advanceTimersByTimeAsync(5000);
    expect(tops()).toEqual(['face|H', 'face|I', 'face colour t-r|']);
    expect(Element.prototype.animate).toHaveBeenCalled();
    expect(window.FlapSound.clack).toHaveBeenCalled();
  });

  it('shows the sound toggle, and turns the sound on and off', () => {
    const toggle = document.querySelector('[data-sound-toggle]');
    expect(toggle.hidden).toBe(false);
    toggle.click();
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    toggle.click();
    expect(toggle.getAttribute('aria-pressed')).toBe('false');
    expect(window.FlapSound.toggle).toHaveBeenCalledTimes(2);
  });

  it('leaves every face of a landed tile showing it, so no old face peeps out', () => {
    for (const el of document.querySelectorAll('.cell')) {
      const faces = [...el.querySelectorAll('.face')].map(f => f.className + '|' + f.textContent);
      expect(new Set(faces).size).toBe(1);
    }
  });
});

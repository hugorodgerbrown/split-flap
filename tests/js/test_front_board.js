// Tests for static/js/front_board.js: the front page's board flips through its demo boards.
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';

const cell = sym => `<div class="cell"><div class="half top"><span class="face">${sym}</span></div><div class="half bottom"><span class="face">${sym}</span></div></div>`;

beforeAll(async () => {
  vi.useFakeTimers();
  // Reduced motion: each board is shown without flipping, so jsdom needs no Web Animations.
  vi.stubGlobal('matchMedia', () => ({ matches: true }));
  vi.stubGlobal('FlapSound', { clack: vi.fn(), toggle: vi.fn() });
  document.body.innerHTML = `
    <button type="button" aria-pressed="false" data-sound-toggle hidden>Sound</button>
    <div class="board" role="img" aria-label="Hi" data-front-board
         data-frames='[["H","I","{r}"],["Y","O",":sun:"]]' data-names='["Morning","Weather"]' data-labels='["Hi","Yo"]'>
      <div class="grid">${cell('H')}${cell('I')}${cell('')}</div>
      <div class="engrave"><span data-board-name>Morning</span><span class="leds"><span class="led on"></span><span class="led"></span></span></div>
    </div>`;
  await import('../../static/js/flaptext.js');
  await import('../../static/js/front_board.js');
});

afterAll(() => {
  document.body.innerHTML = '';
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const faces = () => [...document.querySelectorAll('.cell')].map(c => [...c.querySelectorAll('.face')]);

describe('front board', () => {
  it('keeps the sound toggle hidden, as nothing flips to be heard', () => {
    expect(document.querySelector('[data-sound-toggle]').hidden).toBe(true);
  });

  it('adds the moving leaves to each server-drawn cell', () => {
    expect(document.querySelectorAll('.cell .leaf')).toHaveLength(6);
    expect(faces()[0].map(f => f.textContent)).toEqual(['H', 'H', 'H', 'H']);
  });

  it('moves on to the next board, its name, light and label', () => {
    vi.advanceTimersByTime(8000);
    expect(faces().map(f => f[0].textContent)).toEqual(['Y', 'O', '']);
    // A pictogram is drawn as its mask, in flap ink, with no character.
    expect(faces()[2].every(f => f.className === 'face icon')).toBe(true);
    expect(faces()[2][0].style.getPropertyValue('--icon')).toMatch(/^url\("data:image\/svg\+xml,/);
    expect(document.querySelector('[data-board-name]').textContent).toBe('Weather');
    expect([...document.querySelectorAll('.led')].map(l => l.classList.contains('on'))).toEqual([false, true]);
    expect(document.querySelector('[data-front-board]').getAttribute('aria-label')).toBe('Yo');
  });

  it('comes back round to the first board', () => {
    vi.advanceTimersByTime(6500);
    expect(faces().map(f => f[0].textContent)).toEqual(['H', 'I', '']);
    expect(faces()[2][0].className).toBe('face colour t-r');
    expect(faces()[2][0].style.getPropertyValue('--icon')).toBe('');
  });
});

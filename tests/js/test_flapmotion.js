// Tests for static/js/flapmotion.js: how a board changes from one message to the next.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import '../../static/js/flaptext.js';
import '../../static/js/flapmotion.js';

const { COLS, ROWS, DRUM, DRUM_POS } = self.FlapText;
const { TUNING, nextFlap, waveDelay } = self.FlapMotion;
const SPIN_CAP = TUNING.spinCap;

// The symbols a tile shows, flap by flap, turning from ``from`` to ``to``.
function turn(from, to) {
  const seen = [];
  for (let cur = from; cur !== to; cur = nextFlap(cur, to)) seen.push(nextFlap(cur, to));
  return seen;
}

describe('nextFlap', () => {
  it('steps one symbol round the drum when the target is near', () => {
    expect(turn('A', 'D')).toEqual(['B', 'C', 'D']);
  });

  it('never takes more than SPIN_CAP flaps, however far round the target is', () => {
    for (const from of DRUM) {
      for (const to of DRUM) expect(turn(from, to).length).toBeLessThanOrEqual(SPIN_CAP);
    }
  });

  it('shows no colours or pictograms on the way to a blank', () => {
    // The marks at the end of the characters, then the blank.
    expect(turn('A', ' ')).toEqual(['"', '%', ',', '.', '/', '?', '°', ' ']);
  });

  it('shows no colours or pictograms on the way to any character', () => {
    const characters = DRUM.filter((sym) => sym.length === 1);
    for (const from of DRUM) {
      for (const to of characters) expect(turn(from, to).filter((sym) => sym.length > 1)).toEqual([]);
    }
  });

  it('steps one symbol at a time between letters, as a drum turns', () => {
    const seen = turn('W', 'P');
    for (let i = 1; i < seen.length; i++) {
      expect(DRUM_POS.get(seen[i])).toBe((DRUM_POS.get(seen[i - 1]) + 1) % DRUM.length);
    }
  });

  it('turns through the pictograms on the way to a pictogram', () => {
    expect(turn(':sun:', ':moon:')).toEqual([':cloud:', ':partcloud:', ':rain:', ':storm:', ':snow:', ':moon:']);
  });
});

describe('waveDelay', () => {
  it('starts top left and ends bottom right', () => {
    const delays = [];
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) delays.push(waveDelay(r, c));
    expect(delays[0]).toBe(Math.min(...delays));
    expect(delays.at(-1)).toBe(Math.max(...delays));
  });

  it('sweeps each row left to right', () => {
    for (let c = 1; c < COLS; c++) expect(waveDelay(2, c)).toBeGreaterThan(waveDelay(2, c - 1));
  });

  it('starts each row a beat behind the row above', () => {
    for (let r = 1; r < ROWS; r++) expect(waveDelay(r, 0)).toBeGreaterThan(waveDelay(r - 1, 0));
  });
});

describe('TUNING', () => {
  afterEach(() => Object.assign(TUNING, self.FlapMotion.DEFAULTS));

  it('starts at the committed defaults', () => {
    expect(TUNING).toEqual(self.FlapMotion.DEFAULTS);
  });

  it('changes the cap at once', () => {
    TUNING.spinCap = 3;
    expect(turn('A', ' ')).toEqual(['?', '°', ' ']);
  });

  it('changes the wave at once', () => {
    Object.assign(TUNING, { colMs: 10, rowMs: 100, scatterMs: 0 });
    expect(waveDelay(2, 3)).toBe(230);
  });
});

describe('Board', () => {
  const { Board } = self.FlapMotion;
  let grid;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    Element.prototype.animate = () => ({ cancel() {} });
    grid = document.createElement('div');
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const faces = () => [...grid.querySelectorAll('.cell')].map(c => c.querySelector('.half.top .face').textContent);

  it('draws the 22x6 modules, blank', () => {
    new Board(grid);
    expect(faces()).toHaveLength(COLS * ROWS);
    expect(faces().every(f => f === ' ')).toBe(true);
  });

  it('snaps to a message at once', () => {
    const board = new Board(grid);
    board.snap(['HELLO']);
    expect(faces().slice(0, 5).join('')).toBe('HELLO');
  });

  it('flips to a message, top left first', async () => {
    const board = new Board(grid);
    board.show(['A', '', '', '', '', 'B']);
    await vi.advanceTimersByTimeAsync(TUNING.rowMs * 2);
    expect(faces()[0]).toBe('A');
    expect(faces()[5 * COLS]).toBe(' ');
    await vi.advanceTimersByTimeAsync(5000);
    expect(faces()[5 * COLS]).toBe('B');
  });

  it('schedules a tile afresh after a snap cancels its start', async () => {
    const board = new Board(grid);
    TUNING.colMs = 1000;
    board.show(['', '', '', '', '', ' '.repeat(COLS - 1) + 'A']);
    board.snap([]);
    TUNING.colMs = 0;
    board.show(['', '', '', '', '', ' '.repeat(COLS - 1) + 'B']);
    await vi.advanceTimersByTimeAsync(TUNING.rowMs * 5 + 500);
    expect(faces().at(-1)).toBe('B');
    Object.assign(TUNING, self.FlapMotion.DEFAULTS);
  });

  it('snaps instead of flipping with reduced motion', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const board = new Board(grid);
    board.show(['A']);
    vi.runAllTimers();
    expect(faces()[0]).toBe('A');
  });
});

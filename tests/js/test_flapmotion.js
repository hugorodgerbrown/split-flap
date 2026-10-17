// Tests for static/js/flapmotion.js: how a board changes from one message to the next.
import { describe, expect, it } from 'vitest';

import '../../static/js/flaptext.js';
import '../../static/js/flapmotion.js';

const { COLS, ROWS, DRUM, DRUM_POS } = self.FlapText;
const { SPIN_CAP, nextFlap, waveDelay } = self.FlapMotion;

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

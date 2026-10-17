// Tests for static/js/flaptext.js: how a message lays out on the board.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import '../../static/js/flaptext.js';

const { COLS, ROWS, ICONS, parse, message, wrap } = self.FlapText;
const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const { cases } = JSON.parse(read('../boards/layout_cases.json'));

// Every tile of the board showing ``text``, row by row, as the TV draws it.
function draw(text) {
  return message(text).map((line) => {
    const symbols = parse(line).slice(0, COLS);
    while (symbols.length < COLS) symbols.push(' ');
    return symbols.join('|');
  });
}

describe('message', () => {
  it.each(cases)('draws $text as the server does', ({ text, rows }) => {
    expect(draw(text)).toEqual(rows);
  });

  it('always fills the whole board', () => {
    expect(message('hi')).toHaveLength(ROWS);
  });
});

describe('parse', () => {
  it('reads colours, pictograms and emoji as one tile each', () => {
    expect(parse('{R}:Sun:☀️a')).toEqual(['{r}', ':sun:', ':sun:', 'A']);
  });

  it('shows an unknown :name: as typed', () => {
    expect(parse(':no:')).toEqual([':', 'N', 'O', ':']);
  });
});

describe('wrap', () => {
  it('cuts a word wider than the board into rows', () => {
    expect(wrap('x'.repeat(30))).toEqual(['X'.repeat(COLS), 'X'.repeat(8)]);
  });
});

describe('the app pages\' pictograms', () => {
  it('draw each pictogram as the TV does', () => {
    const sprite = read('../../static/img/pictograms.svg');
    const drawn = Object.fromEntries(
      [...sprite.matchAll(/<symbol id="([a-z]+)"[^>]*>(.*?)<\/symbol>/g)].map((m) => [m[1], m[2]]),
    );
    const expected = Object.fromEntries(
      Object.entries(ICONS).map(([name, svg]) => [name, svg.replaceAll('"black"', '"currentColor"')]),
    );
    expect(drawn).toEqual(expected);
  });
});

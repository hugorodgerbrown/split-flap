// Tests for static/js/board_motion.js: the display page's preview flips on
// Save, a Routine's post and Replay, through flapmotion.js's Board.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import '../../static/js/flaptext.js';
import '../../static/js/flapmotion.js';
import '../../static/js/board_motion.js';

const { Board } = self.FlapMotion;
const { BoardMotion } = self;

const PREVIEW = (name, text) => `
  <div class="board board--fluid" id="display-preview" data-flapboard data-name="${name}" data-text="${text}">
    <div class="grid" data-flapboard-grid><div class="cell">server drawn</div></div>
  </div>`;

// What the board turned to, row by row, trimmed: the first row with something on it.
const said = (call) => (call[0].find((line) => line.trim()) ?? '').trim().toUpperCase();

let snap, show;

beforeEach(() => {
  vi.stubGlobal('matchMedia', () => ({ matches: false }));
  Element.prototype.animate = () => ({ cancel() {} });
  snap = vi.spyOn(Board.prototype, 'snap');
  show = vi.spyOn(Board.prototype, 'show');
});

afterEach(() => {
  document.body.innerHTML = '';
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  delete Element.prototype.animate;
});

describe('attach', () => {
  it('swaps the still drawing for flap modules showing the same message, without flipping', () => {
    document.body.innerHTML = PREVIEW('News', 'Hello');
    const preview = document.getElementById('display-preview');
    BoardMotion.attach(preview);
    expect(preview.querySelectorAll('.cell .leaf')).toHaveLength(132 * 2);
    expect(said(snap.mock.calls[0])).toBe('HELLO');
    expect(show).not.toHaveBeenCalled();
    expect(BoardMotion.attach(preview)).toBe(preview.motion);  // once only
  });
});

describe('flip', () => {
  beforeEach(() => {
    document.body.innerHTML = PREVIEW('News', 'Old');
  });

  it('turns from one message to the other, and remembers the new one', () => {
    const preview = document.getElementById('display-preview');
    BoardMotion.flip(preview, 'Old', 'New');
    expect(said(snap.mock.lastCall)).toBe('OLD');
    expect(said(show.mock.lastCall)).toBe('NEW');
    expect(preview.dataset.text).toBe('New');
  });

  it('flips when board_preview.js says a Routine posted', () => {
    const preview = document.getElementById('display-preview');
    preview.dispatchEvent(new CustomEvent('board:post', { bubbles: true, detail: { from: 'Old', to: 'Sunny' } }));
    expect(said(snap.mock.lastCall)).toBe('OLD');
    expect(said(show.mock.lastCall)).toBe('SUNNY');
  });

  it('replays from blank when Replay is pressed', () => {
    document.body.insertAdjacentHTML('beforeend', '<form id="replay"></form>');
    document.getElementById('replay').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    expect(said(snap.mock.lastCall)).toBe('');
    expect(said(show.mock.lastCall)).toBe('OLD');
  });
});

describe('Save', () => {
  it('flips the swapped-in preview from the message that was live', () => {
    document.body.innerHTML = `${PREVIEW('News', 'Draft text')}
      <form data-board-editor data-preview="display-preview" data-name="News" data-saved="Old"></form>`;
    const form = document.querySelector('form');
    document.dispatchEvent(new CustomEvent('htmx:beforeRequest', { detail: { elt: form } }));
    document.body.innerHTML = PREVIEW('News', 'Draft text');  // htmx swaps in the saved board
    document.dispatchEvent(new Event('htmx:afterSettle'));
    expect(said(snap.mock.lastCall)).toBe('OLD');
    expect(said(show.mock.lastCall)).toBe('DRAFT TEXT');
  });

  it("doesn't flip a board you switched to", () => {
    document.body.innerHTML = `${PREVIEW('News', 'Old')}
      <form data-board-editor data-preview="display-preview" data-name="News" data-saved="Old"></form>`;
    document.dispatchEvent(new CustomEvent('htmx:beforeRequest', { detail: { elt: document.querySelector('form') } }));
    document.body.innerHTML = PREVIEW('Weather', 'Rain');
    document.dispatchEvent(new Event('htmx:afterSettle'));
    expect(show).not.toHaveBeenCalled();
  });

  it('ignores requests from anything but the editor', () => {
    document.body.innerHTML = `${PREVIEW('News', 'Old')}<form id="sound"></form>`;
    document.dispatchEvent(new CustomEvent('htmx:beforeRequest', { detail: { elt: document.getElementById('sound') } }));
    document.dispatchEvent(new Event('htmx:afterSettle'));
    expect(show).not.toHaveBeenCalled();
  });
});

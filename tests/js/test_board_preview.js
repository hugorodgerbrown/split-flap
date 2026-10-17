// Tests for static/js/board_preview.js: the display page's preview, its board
// editor and palette, and the preview following the server.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import '../../static/js/flaptext.js';
import '../../static/js/board_preview.js';

const { BoardPreview } = self;

const BOARD = `
  <div class="board board--fluid" id="preview" data-flapboard data-pictograms="/static/img/pictograms.svg">
    <div class="grid" data-flapboard-grid></div>
    <div class="engrave"><span>News</span><span data-flapboard-tag>On the display</span></div>
  </div>`;

const tiles = () => [...document.querySelectorAll('[data-flapboard-grid] > .cell')];
// What the top halves say: each cell shows one face in both halves.
const shown = () => tiles().map((t) => t.querySelector('.top').textContent).join('').trim();

afterEach(() => {
  document.body.innerHTML = '';
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('draw', () => {
  beforeEach(() => {
    document.body.innerHTML = BOARD;
  });

  it('draws every tile, with colours and pictograms', () => {
    const board = document.getElementById('preview');
    BoardPreview.draw(board, 'News', '{g} Hi :train:');
    expect(tiles()).toHaveLength(22 * 6);
    expect(document.querySelectorAll('.face.colour.t-g')).toHaveLength(2);
    expect(document.querySelector('.face__icon use').getAttribute('href')).toBe('/static/img/pictograms.svg#train');
    expect(shown()).toBe('HI');
    expect(board.getAttribute('aria-label')).toBe('News: {g} Hi :train:');
  });
});

describe('measure', () => {
  it('counts the rows, and says when they are more than the board has', () => {
    expect(BoardPreview.measure('   ')).toEqual({ rows: 0, fits: true });
    expect(BoardPreview.measure('one\ntwo')).toEqual({ rows: 2, fits: true });
    expect(BoardPreview.measure('r\n'.repeat(7))).toEqual({ rows: 7, fits: false });
  });
});

describe('editor', () => {
  let form, textarea, save, palette;

  beforeEach(() => {
    document.body.innerHTML = `${BOARD}
      <form data-board-editor data-preview="preview" data-name="News" data-saved="Old" data-max-length="400">
        <textarea name="text">Old</textarea>
        <p><span data-row-count></span><span data-char-count></span></p>
        <div data-palette hidden><button type="button" data-insert=":sun:">Sun</button></div>
        <button type="submit" data-save>Save</button>
      </form>`;
    form = document.querySelector('form');
    textarea = form.querySelector('textarea');
    save = form.querySelector('[data-save]');
    palette = form.querySelector('[data-palette]');
    BoardPreview.editor(form);
  });

  const type = (value) => {
    textarea.value = value;
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  };
  const tag = () => document.querySelector('[data-flapboard-tag]').textContent;

  it('starts on what the display shows, with Save off and the palette out', () => {
    expect(shown()).toBe('OLD');
    expect(tag()).toBe('On the display');
    expect(save.disabled).toBe(true);
    expect(palette.hidden).toBe(false);
    expect(form.querySelector('[data-row-count]').textContent).toBe('1 of 6 rows');
    expect(form.querySelector('[data-char-count]').textContent).toBe('3 / 400');
  });

  it('follows the box as a draft, and turns Save on', () => {
    type('New');
    expect(shown()).toBe('NEW');
    expect(tag()).toBe('Draft');
    expect(save.disabled).toBe(false);
  });

  it('shows the board\'s name while the box is empty', () => {
    type('');
    expect(shown()).toBe('NEWS');
  });

  it('keeps Save off for a message that would lose its end', () => {
    type('r\n'.repeat(7));
    const count = form.querySelector('[data-row-count]');
    expect(count.textContent).toBe('7 of 6 rows: shorten it so nothing is cut off');
    expect(count.classList.contains('editor__count--over')).toBe(true);
    expect(save.disabled).toBe(true);
  });

  it('adds a palette key\'s code where the cursor is', () => {
    textarea.setSelectionRange(1, 1);
    palette.querySelector('button').click();
    expect(textarea.value).toBe('O:sun:ld');
    expect(document.querySelector('use').getAttribute('href')).toMatch(/#sun$/);
    expect(save.disabled).toBe(false);
  });
});

describe('live', () => {
  const state = (posted_at, message) => ({
    status: 200,
    headers: { get: () => '"v' + posted_at + '"' },
    json: async () => ({ boards: [{ name: 'News', message, posted_at }] }),
  });

  beforeEach(() => {
    document.body.innerHTML = `${BOARD}
      <p data-live-board="News" data-state-url="/d/x/state/" data-poll-seconds="5" data-preview="preview">
        <span data-posted>Nothing posted yet, so the display shows its name.</span>
      </p>`;
  });

  it('redraws when the board gets a new message, and sends the ETag it has', async () => {
    vi.useFakeTimers();
    const fetch = vi.fn()
      .mockResolvedValueOnce(state(null, ''))
      .mockResolvedValueOnce({ status: 304 })
      .mockResolvedValueOnce(state('2026-10-17T07:00:00+01:00', 'Sunny'));
    vi.stubGlobal('fetch', fetch);

    BoardPreview.live(document.querySelector('[data-live-board]'));
    await vi.advanceTimersByTimeAsync(0);
    expect(tiles()).toHaveLength(0);  // the server's drawing stands until something changes
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetch.mock.calls[1][1].headers['If-None-Match']).toBe('"vnull"');
    await vi.advanceTimersByTimeAsync(5000);
    expect(shown()).toBe('SUNNY');
    expect(document.querySelector('[data-posted] time').dateTime).toBe('2026-10-17T07:00:00+01:00');
  });

  it('draws a post that landed before the first answer', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(state('2026-10-17T07:00:00+00:00', 'Early')));
    BoardPreview.live(document.querySelector('[data-live-board]'));
    await vi.advanceTimersByTimeAsync(0);
    expect(shown()).toBe('EARLY');
  });

  it('leaves the server\'s drawing alone while nothing has changed', async () => {
    vi.useFakeTimers();
    const status = document.querySelector('[data-live-board]');
    status.dataset.postedAt = '2026-10-17T07:00:00+00:00';
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(state('2026-10-17T07:00:00+00:00', 'Same')));
    BoardPreview.live(status);
    await vi.advanceTimersByTimeAsync(0);
    expect(tiles()).toHaveLength(0);
  });

  describe('beside the board editor', () => {
    let form, textarea;

    beforeEach(() => {
      document.body.insertAdjacentHTML('beforeend', `
        <form data-board-editor data-preview="preview" data-name="News" data-saved="Old" data-max-length="400">
          <textarea name="text">Old</textarea>
          <p><span data-row-count></span><span data-char-count></span></p>
          <button type="submit" data-save>Save</button>
        </form>`);
      form = document.querySelector('form');
      textarea = form.querySelector('textarea');
      BoardPreview.editor(form);
      vi.useFakeTimers();
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(state('2026-10-17T07:00:00+00:00', 'Sunny')));
    });

    it('puts a new post in the editor too, so Save stays off', async () => {
      BoardPreview.live(document.querySelector('[data-live-board]'));
      await vi.advanceTimersByTimeAsync(0);
      expect(textarea.value).toBe('Sunny');
      expect(shown()).toBe('SUNNY');
      expect(form.querySelector('[data-save]').disabled).toBe(true);
    });

    it('leaves a draft alone, but measures it against the new post', async () => {
      textarea.value = 'Mine';
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      BoardPreview.live(document.querySelector('[data-live-board]'));
      await vi.advanceTimersByTimeAsync(0);
      expect(textarea.value).toBe('Mine');
      expect(shown()).toBe('MINE');
      expect(document.querySelector('[data-posted] time')).not.toBeNull();
      textarea.value = 'Old';  // back to what the box first held, which is no longer on the display
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      expect(form.querySelector('[data-save]').disabled).toBe(false);
    });
  });

  it('keeps what it drew when the network is away', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    BoardPreview.live(document.querySelector('[data-live-board]'));
    await vi.advanceTimersByTimeAsync(5000);
    expect(document.querySelector('[data-posted]').textContent).toMatch(/Nothing posted yet/);
  });
});

describe('after htmx swaps in another board', () => {
  const page = (name) => `${BOARD}
    <p data-live-board="${name}" data-state-url="/d/x/state/" data-poll-seconds="5" data-preview="preview"><span data-posted></span></p>
    <form data-board-editor data-preview="preview" data-name="${name}" data-saved="${name} news" data-max-length="400">
      <textarea name="text">${name} news</textarea>
      <p><span data-row-count></span><span data-char-count></span></p>
      <button type="submit" data-save>Save</button>
    </form>`;

  it('wires up the new board once, and stops polling for the old one', () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockResolvedValue({ status: 304 });
    vi.stubGlobal('fetch', fetch);
    const stop = vi.spyOn(globalThis, 'clearInterval');
    document.body.innerHTML = page('News');
    document.dispatchEvent(new Event('htmx:afterSettle'));
    expect(shown()).toBe('NEWSNEWS');
    document.dispatchEvent(new Event('htmx:afterSettle'));  // a swap elsewhere: nothing new
    expect(fetch).toHaveBeenCalledTimes(1);
    document.body.innerHTML = page('Weather');
    document.dispatchEvent(new Event('htmx:afterSettle'));
    expect(shown()).toBe('WEATHERNEWS');
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(stop).toHaveBeenCalledTimes(2);  // before each new poller starts
  });
});

describe('posted', () => {
  it('says when nothing has been posted', () => {
    const line = document.createElement('span');
    BoardPreview.posted(line, null);
    expect(line.textContent).toBe('Nothing posted yet, so the display shows its name.');
  });
});

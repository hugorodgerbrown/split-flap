/*
 * static/js/board_preview.js — the board drawn still on the app's pages, kept up to date.
 *
 * The server draws each board as it stands (boards/_flapboard.html, styled
 * by board.css), so
 * the pages work without this file. With it:
 *
 * - the board page's preview follows the message box as you type, says
 *   "Draft" while it differs from what the display shows, counts the rows,
 *   and keeps Save off until there's a change that fits;
 * - the palette shows, and each key adds its code where the cursor is;
 * - the display page's preview asks the server what the board shows, so a
 *   Routine's post appears without a reload.
 *
 * Layout comes from flaptext.js, which the TV's board uses too.
 */
(function () {
  'use strict';

  const SVG = 'http://www.w3.org/2000/svg';
  const DRAFT = 'Draft';
  const SAVED = 'On the display';
  const NOTES = {
    [DRAFT]: 'Draft: the display still shows the last message until you save this one.',
    [SAVED]: 'This is what the display shows on this board now.',
  };

  function face(symbol, pictograms) {
    const el = document.createElement('span');
    el.className = 'face';
    if (symbol[0] === '{') {
      el.className = 'face colour t-' + symbol[1];
    } else if (symbol.length > 1) {
      const svg = document.createElementNS(SVG, 'svg');
      svg.setAttribute('class', 'face__icon');
      svg.setAttribute('aria-hidden', 'true');
      const use = document.createElementNS(SVG, 'use');
      use.setAttribute('href', pictograms + '#' + symbol.slice(1, -1));
      svg.appendChild(use);
      el.appendChild(svg);
    } else {
      el.textContent = symbol.trim();
    }
    return el;
  }

  // One still flap module, as board.css draws it: two halves showing one face.
  function cell(symbol, pictograms) {
    const el = document.createElement('div');
    el.className = 'cell';
    ['half top', 'half bottom'].forEach(function (cls) {
      const half = document.createElement('div');
      half.className = cls;
      half.appendChild(face(symbol, pictograms));
      el.appendChild(half);
    });
    return el;
  }

  // Draw ``text`` on a board, as the display would show it.
  function draw(board, name, text) {
    const { COLS, parse, message } = self.FlapText;
    const tiles = [];
    message(text).forEach(function (line) {
      const symbols = parse(line).slice(0, COLS);
      while (symbols.length < COLS) symbols.push(' ');
      symbols.forEach(function (symbol) {
        tiles.push(cell(symbol, board.dataset.pictograms));
      });
    });
    board.querySelector('[data-flapboard-grid]').replaceChildren(...tiles);
    board.setAttribute('aria-label', name + ': ' + text);
  }

  // How many rows a message fills, and whether that's more than the board has.
  function measure(text) {
    const { ROWS, wrap } = self.FlapText;
    const rows = text.trim() ? wrap(text.trim()).length : 0;
    return { rows: rows, fits: rows <= ROWS };
  }

  function insert(textarea, code) {
    const start = textarea.selectionStart ?? textarea.value.length;
    const end = textarea.selectionEnd ?? start;
    textarea.setRangeText(code, start, end, 'end');
    textarea.focus();
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function editor(form) {
    const board = document.getElementById(form.dataset.preview);
    const textarea = form.querySelector('textarea');
    const save = form.querySelector('[data-save]');
    const rowCount = form.querySelector('[data-row-count]');
    const charCount = form.querySelector('[data-char-count]');
    const tag = board.querySelector('[data-flapboard-tag]');
    const note = document.querySelector('[data-draft-note]');
    const { ROWS } = self.FlapText;

    function update() {
      const text = textarea.value;
      const { rows, fits } = measure(text);
      const draft = text.trim() !== form.dataset.saved.trim();
      draw(board, form.dataset.name, text.trim() || form.dataset.name);
      tag.textContent = draft ? DRAFT : SAVED;
      if (note) note.textContent = NOTES[tag.textContent];
      rowCount.textContent = fits
        ? rows + ' of ' + ROWS + ' rows'
        : rows + ' of ' + ROWS + ' rows: shorten it so nothing is cut off';
      rowCount.classList.toggle('editor__count--over', !fits);
      charCount.textContent = text.length + ' / ' + form.dataset.maxLength;
      save.disabled = !draft || !fits;
    }

    textarea.addEventListener('input', update);
    form.querySelectorAll('[data-palette]').forEach(function (palette) {
      palette.hidden = false;
      palette.addEventListener('click', function (event) {
        const key = event.target.closest('[data-insert]');
        if (key) insert(textarea, key.dataset.insert);
      });
    });
    update();
    return update;
  }

  const WHEN = { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' };

  function posted(line, at) {
    if (!at) {
      line.textContent = 'Nothing posted yet, so the display shows its name.';
      return;
    }
    const time = document.createElement('time');
    time.dateTime = at;
    time.textContent = new Date(at).toLocaleString('en-GB', WHEN);
    line.replaceChildren('Posted ', time);
  }

  // Keep the display page's preview on what the server says the board shows.
  function live(status) {
    const board = document.getElementById(status.dataset.preview);
    const name = status.dataset.liveBoard;
    let etag = null;
    let shown = status.dataset.postedAt || null;  // posted_at as the server drew it

    async function poll() {
      try {
        const response = await fetch(status.dataset.stateUrl, {
          headers: etag ? { 'If-None-Match': etag } : {},
        });
        if (response.status === 200) {
          etag = response.headers.get('ETag');
          const state = await response.json();
          const found = state.boards.find(function (b) { return b.name === name; });
          if (found && found.posted_at !== shown) {
            draw(board, name, found.message || name);
            posted(status.querySelector('[data-posted]'), found.posted_at);
            shown = found.posted_at;
          }
        }
      } catch (error) {
        // Offline, or the server's away: keep what's drawn and try again.
      }
    }

    poll();
    return setInterval(poll, Number(status.dataset.pollSeconds) * 1000);
  }

  function start() {
    document.querySelectorAll('form[data-board-editor]').forEach(editor);
    document.querySelectorAll('[data-live-board]').forEach(live);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();

  self.BoardPreview = { draw: draw, measure: measure, insert: insert, editor: editor, live: live, posted: posted };
})();

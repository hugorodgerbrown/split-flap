/*
 * static/js/board_motion.js — the display page's preview flips like the TV.
 *
 * board_preview.js draws the preview still; with this file each preview
 * gets a FlapMotion.Board (static/js/flapmotion.js) and turns, as the TV
 * does, from the message that was live to the new one:
 *
 * - on Save, which htmx posts so the page stays put;
 * - when a Routine's post lands (board_preview.js says so with a
 *   "board:post" event), unless you're mid-draft;
 * - on Replay, from blank.
 *
 * While you type, board_preview.js snaps it to your draft. Not in the
 * precached shell: offline, the preview stays still.
 *
 * While the display's Sound switch is on, the preview clacks too
 * (static/js/flap_sound.js). Browsers hold sound until a tap, so the first
 * tap or key press on the page readies it; the switch is read at each clack,
 * so turning it off silences the preview at once.
 */
(function () {
  'use strict';

  const { Board } = self.FlapMotion;
  const { message } = self.FlapText;

  // Whether the display's Sound switch is on.
  function soundOn() {
    const toggle = document.querySelector('#sound [role="switch"]');
    return Boolean(toggle) && toggle.getAttribute('aria-checked') === 'true';
  }

  function clack() {
    if (soundOn() && self.FlapSound) self.FlapSound.play();
  }

  // Give a still preview a Board of its own, showing what it shows now.
  function attach(preview) {
    if (preview.motion) return preview.motion;
    const grid = preview.querySelector('[data-flapboard-grid]');
    grid.replaceChildren();
    preview.motion = new Board(grid, { clack: clack });
    preview.motion.snap(message(preview.dataset.text));
    return preview.motion;
  }

  // Turn ``preview`` from ``from`` to ``to`` in the TV's diagonal wave.
  function flip(preview, from, to) {
    const board = attach(preview);
    board.snap(message(from));
    board.show(message(to));
    preview.dataset.text = to;
  }

  // What Save is about to replace: the live message, and the board it's on.
  let saving = null;

  function start() {
    document.querySelectorAll('[data-flapboard]').forEach(attach);
    if (!saving) return;
    const preview = document.getElementById(saving.preview);
    if (preview && preview.dataset.name === saving.name) flip(preview, saving.text, preview.dataset.text);
    saving = null;
  }

  document.addEventListener('htmx:beforeRequest', function (event) {
    const form = event.detail.elt;
    if (!form.matches || !form.matches('form[data-board-editor]')) return;
    saving = { preview: form.dataset.preview, name: form.dataset.name, text: form.dataset.saved || form.dataset.name };
  });
  document.addEventListener('htmx:afterSettle', start);
  document.addEventListener('board:post', function (event) {
    flip(event.target, event.detail.from, event.detail.to);
  });
  document.addEventListener('submit', function (event) {
    if (event.target.id !== 'replay') return;
    const preview = document.querySelector('[data-flapboard]');
    if (preview) flip(preview, '', preview.dataset.text);
  });

  // Ready the sound at a tap or key press; a touch counts once the finger lifts.
  ['pointerup', 'keydown'].forEach(function (type) {
    document.addEventListener(type, function () {
      if (self.FlapSound && document.querySelector('#sound [role="switch"]')) self.FlapSound.unlock();
    }, { capture: true });
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();

  self.BoardMotion = { attach: attach, flip: flip };
})();

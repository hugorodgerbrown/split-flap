/*
 * static/js/board_tuning.js — the board tuning page (/app/design/board/).
 *
 * Draws a live board (FlapMotion.Board) and ties each slider to one number
 * in FlapMotion.TUNING, so the next Replay uses it. "Values" shows the
 * current numbers as code to paste into static/js/flapmotion.js. Nothing is
 * saved: a reload starts from the code's values again.
 */
(() => {
  const form = document.querySelector('[data-tuning]');
  if (!form) return;
  const { DEFAULTS, TUNING, Board } = self.FlapMotion;
  const boards = JSON.parse(form.dataset.boards);
  const board = new Board(document.querySelector('[data-tuning-grid]'));
  const nameEl = document.querySelector('[data-tuning-name]');
  const valuesEl = document.querySelector('[data-tuning-values]');
  const copyButton = valuesEl.parentElement.querySelector('[data-copy]');
  const sliders = [...form.querySelectorAll('input[type="range"]')];

  // TUNING as the line of code that would set it.
  function code() {
    const pairs = Object.keys(DEFAULTS).map(key => `${key}: ${TUNING[key]}`);
    return `{ ${pairs.join(', ')} }`;
  }

  function sync() {
    sliders.forEach(input => {
      input.value = TUNING[input.name];
      form.querySelector(`[data-tuning-value="${input.name}"]`).value = TUNING[input.name];
    });
    valuesEl.textContent = code();
    copyButton.dataset.copy = code();
  }

  const chosen = name => boards[+form.elements[name].value];
  // Show the "from" board at once, then flip to the "to" board.
  function replay() {
    board.snap(chosen('from').lines);
    nameEl.textContent = chosen('to').name;
    setTimeout(() => board.show(chosen('to').lines), 300);
  }

  form.addEventListener('input', event => {
    if (event.target.type !== 'range') return;
    TUNING[event.target.name] = +event.target.value;
    sync();
  });
  form.querySelector('[data-replay]').addEventListener('click', replay);
  form.querySelector('[data-reset]').addEventListener('click', () => {
    Object.assign(TUNING, DEFAULTS);
    sync();
  });

  sync();
  board.snap(chosen('from').lines);
  nameEl.textContent = chosen('from').name;
})();

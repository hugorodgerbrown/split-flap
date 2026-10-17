/*
 * static/js/flaptext.js — how a message lays out on the board's 22x6 tiles.
 *
 * Shared by the TV's board (splitflap.js) and the app's preview
 * (board_preview.js), so both draw a message the same way. The server
 * mirrors it in apps/boards/layout.py, and tests/boards/test_layout.py
 * holds the two to the same tables.
 */
(() => {
  const COLS = 22, ROWS = 6;
  // Pictograms printed in flap ink, each a 24x24 line drawing.
  const CLOUD = 'M7 14h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.1 7 3.5 3.5 0 0 0 7 14z';
  const ICONS = {
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/>',
    cloud: '<path d="M7 18h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6.1 11 3.5 3.5 0 0 0 7 18z"/>',
    partcloud: '<path d="M8.5 3v1.5M3 8.5h1.5M4.6 4.6l1 1M12.4 4.6l-1 1"/><path d="M5.6 11.2a3.5 3.5 0 1 1 6.3-2.9"/><path d="M9 20h8a3.5 3.5 0 0 0 .4-6.98A5 5 0 0 0 8.2 14 3 3 0 0 0 9 20z"/>',
    rain: `<path d="${CLOUD}"/><path d="M8 17l-1 3.5M12 17l-1 3.5M16 17l-1 3.5"/>`,
    storm: `<path d="${CLOUD}"/><path d="M12.5 15l-2.5 3.5h4L11.5 22"/>`,
    snow: '<path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9M9.5 4.5L12 6l2.5-1.5M9.5 19.5L12 18l2.5 1.5"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    umbrella: '<path d="M12 3a9 9 0 0 1 9 9H3a9 9 0 0 1 9-9z"/><path d="M12 12v7a2 2 0 0 0 4 0"/>',
    train: '<rect x="6" y="3" width="12" height="14" rx="3"/><path d="M6 10h12M9 13.5h.01M15 13.5h.01M9 17l-2 4M15 17l2 4"/>',
    plane: '<path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z" fill="black" stroke="none"/>',
    car: '<path d="M5 17h14v-5l-2-5H7l-2 5v5zM5 12h14"/><circle cx="8" cy="17" r="1.6"/><circle cx="16" cy="17" r="1.6"/>',
    bike: '<circle cx="6" cy="16" r="3.5"/><circle cx="18" cy="16" r="3.5"/><path d="M6 16l4-7h5l3 7M10 9l2 7h6M13.5 6H16"/>',
    home: '<path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/>',
    coffee: '<path d="M5 9h11v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V9zM16 11h1.5a2.5 2.5 0 0 1 0 5H16M8 3.5v2.5M11 3.5v2.5M14 3.5v2.5"/>',
    music: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    news: '<rect x="4" y="5" width="16" height="14" rx="1.5"/><path d="M7.5 9h9M7.5 12h9M7.5 15h5"/>',
    heart: '<path d="M12 20s-7.5-4.6-7.5-10.2A4.2 4.2 0 0 1 12 7.3a4.2 4.2 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z" fill="black"/>',
    star: '<path d="M12 3l2.6 6 6.4.3-5 4.1 1.8 6.6-5.8-3.7-5.8 3.7L8 13.4 3 9.3 9.4 9z" fill="black"/>',
    smile: '<circle cx="12" cy="12" r="9"/><path d="M8 14a4.6 4.6 0 0 0 8 0"/><circle cx="9" cy="9.8" r=".9" fill="black"/><circle cx="15" cy="9.8" r=".9" fill="black"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    cross: '<path d="M6 6l12 12M18 6L6 18"/>',
    up: '<path d="M12 20V4M6 10l6-6 6 6"/>',
    down: '<path d="M12 4v16M6 14l6 6 6-6"/>',
    left: '<path d="M20 12H4M10 6l-6 6 6 6"/>',
    right: '<path d="M4 12h16M14 6l6 6-6 6"/>',
  };
  // Emoji people type, mapped onto the pictograms above.
  const EMOJI = {
    '☀': 'sun', '🌞': 'sun', '☁': 'cloud', '⛅': 'partcloud', '🌤': 'partcloud', '🌥': 'partcloud',
    '🌧': 'rain', '🌦': 'rain', '⛈': 'storm', '⚡': 'storm', '🌩': 'storm', '❄': 'snow', '🌨': 'snow',
    '🌙': 'moon', '🌛': 'moon', '☂': 'umbrella', '☔': 'umbrella',
    '🚆': 'train', '🚂': 'train', '🚄': 'train', '🚇': 'train', '🚉': 'train', '✈': 'plane', '🛫': 'plane',
    '🚗': 'car', '🚕': 'car', '🚲': 'bike', '🏠': 'home', '🏡': 'home', '☕': 'coffee',
    '🎵': 'music', '🎶': 'music', '♪': 'music', '♫': 'music', '📰': 'news',
    '❤': 'heart', '♥': 'heart', '💛': 'heart', '💙': 'heart', '💚': 'heart', '🧡': 'heart', '💜': 'heart',
    '★': 'star', '⭐': 'star', '🌟': 'star', '😀': 'smile', '😃': 'smile', '😊': 'smile', '🙂': 'smile', '😄': 'smile',
    '✓': 'check', '✔': 'check', '✅': 'check', '✗': 'cross', '✘': 'cross', '❌': 'cross',
    '↑': 'up', '⬆': 'up', '↓': 'down', '⬇': 'down', '←': 'left', '⬅': 'left', '→': 'right', '➡': 'right',
  };

  // The drum: every symbol a flap can show, in the order it turns through them.
  const DRUM = [' ', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ', ...'1234567890', ...'!@#$()-+&=;:\'"%,./?°',
    '{r}', '{o}', '{y}', '{g}', '{b}', '{v}', '{w}', ...Object.keys(ICONS).map(k => `:${k}:`)];
  const DRUM_POS = new Map(DRUM.map((s, i) => [s, i]));
  // Each pictogram as a CSS mask, painted in flap ink by board.css (.face.icon).
  const ICON_MASKS = Object.fromEntries(Object.entries(ICONS).map(([k, svg]) => [k,
    `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">${svg}</svg>`)}")`]));
  const ALIASES = { '’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-', '…': '.' };

  function parse(str) {
    const out = [];
    for (const m of String(str).matchAll(/\{([roygbvw])\}|:([a-z]+):|\p{Extended_Pictographic}\uFE0F?|[\s\S]/giu)) {
      if (m[1]) { out.push(`{${m[1].toLowerCase()}}`); continue; }
      const icon = m[2] ? (ICONS[m[2].toLowerCase()] && m[2].toLowerCase()) : EMOJI[m[0].replace('\uFE0F', '')];
      if (icon) { out.push(`:${icon}:`); continue; }
      if (m[2]) { out.push(':', ...parse(m[0].slice(1))); continue; }  // not a known name: show it as typed
      let ch = ALIASES[m[0]] || m[0].toUpperCase();
      if (ch === '\n') ch = ' ';
      out.push(DRUM_POS.has(ch) ? ch : ' ');
    }
    return out;
  }
  const len = s => parse(s).length;
  const pad = n => ' '.repeat(Math.max(0, n));
  const center = s => pad(Math.floor((COLS - len(s)) / 2)) + s;
  function wrap(text, width = COLS) {
    const lines = [];
    for (const para of String(text).split(/\n/)) {
      let line = '';
      for (const word of para.split(/\s+/).filter(Boolean)) {
        const next = line ? line + ' ' + word : word;
        if (len(next) <= width) { line = next; continue; }
        if (line) lines.push(line);
        line = word;
        while (len(line) > width) { lines.push(parse(line).slice(0, width).join('')); line = parse(line).slice(width).join(''); }
      }
      lines.push(line);
    }
    return lines;
  }
  function message(text) {
    const lines = wrap(text).slice(0, ROWS);
    const top = Math.floor((ROWS - lines.length) / 2);
    return Array.from({ length: ROWS }, (_, r) => center(lines[r - top] ?? ''));
  }

  self.FlapText = { COLS, ROWS, ICONS, ICON_MASKS, EMOJI, ALIASES, DRUM, DRUM_POS, parse, len, wrap, message };
})();

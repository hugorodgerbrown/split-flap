"""How a message lays out on the board's tiles, mirroring static/js/flaptext.js.

The TV wraps a message into rows of ``COLS`` tiles and shows ``ROWS`` of
them. The server wraps it the same way so a message that won't fit is
refused when it's posted, rather than losing its tail on the TV, and so the
app's pages can draw the board before (or without) any script.
"""

from __future__ import annotations

import re
from typing import NamedTuple

COLS = 22
ROWS = 6

# The pictograms the board can draw, as :name:, in the order of ICONS in flaptext.js.
PICTOGRAMS = (
    "sun",
    "cloud",
    "partcloud",
    "rain",
    "storm",
    "snow",
    "moon",
    "umbrella",
    "train",
    "plane",
    "car",
    "bike",
    "home",
    "coffee",
    "music",
    "news",
    "heart",
    "star",
    "smile",
    "check",
    "cross",
    "up",
    "down",
    "left",
    "right",
)
ICON_NAMES = frozenset(PICTOGRAMS)

# Emoji people type, mapped onto the pictograms (EMOJI in flaptext.js).
EMOJI = {
    **dict.fromkeys(["☀", "🌞"], "sun"),
    "☁": "cloud",
    **dict.fromkeys(["⛅", "🌤", "🌥"], "partcloud"),
    **dict.fromkeys(["🌧", "🌦"], "rain"),
    **dict.fromkeys(["⛈", "⚡", "🌩"], "storm"),
    **dict.fromkeys(["❄", "🌨"], "snow"),
    **dict.fromkeys(["🌙", "🌛"], "moon"),
    **dict.fromkeys(["☂", "☔"], "umbrella"),
    **dict.fromkeys(["🚆", "🚂", "🚄", "🚇", "🚉"], "train"),
    **dict.fromkeys(["✈", "🛫"], "plane"),
    **dict.fromkeys(["🚗", "🚕"], "car"),
    "🚲": "bike",
    **dict.fromkeys(["🏠", "🏡"], "home"),
    "☕": "coffee",
    **dict.fromkeys(["🎵", "🎶", "♪", "♫"], "music"),
    "📰": "news",
    **dict.fromkeys(["❤", "♥", "💛", "💙", "💚", "🧡", "💜"], "heart"),
    **dict.fromkeys(["★", "⭐", "🌟"], "star"),
    **dict.fromkeys(["😀", "😃", "😊", "🙂", "😄"], "smile"),
    **dict.fromkeys(["✓", "✔", "✅"], "check"),
    **dict.fromkeys(["✗", "✘", "❌"], "cross"),
    **dict.fromkeys(["↑", "⬆"], "up"),
    **dict.fromkeys(["↓", "⬇"], "down"),
    **dict.fromkeys(["←", "⬅"], "left"),
    **dict.fromkeys(["→", "➡"], "right"),
}

# Typographic marks shown as the plain character the drum has (ALIASES).
ALIASES = {
    "\u2019": "'",  # right single quote
    "\u2018": "'",  # left single quote
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
    "\u2026": ".",  # ellipsis
}

# The characters a flap can show (DRUM, less the colours and pictograms).
CHARACTERS = frozenset(" ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$()-+&=;:'\"%,./?°")

# The colour tiles, by the letter in their {code}.
COLOURS = {
    "r": "Red",
    "o": "Orange",
    "y": "Yellow",
    "g": "Green",
    "b": "Blue",
    "v": "Violet",
    "w": "White",
}

# One tile each: a colour code, a :name:, an emoji (with its variation
# selector) or any other single character. Python's re has no
# \p{Extended_Pictographic}, so the emoji blocks stand in for it.
_TILE = re.compile(
    r"\{([roygbvw])\}|:([a-z]+):"
    r"|[\u2190-\u21ff\u2300-\u23ff\u2600-\u27bf\u2b00-\u2bff\U0001f000-\U0001faff]\ufe0f?"
    r"|.",
    re.IGNORECASE | re.DOTALL,
)


def parse(text: str) -> list[str]:
    """Return the symbol on each tile of ``text``, as flaptext.js reads it.

    A symbol is ``{r}`` for a colour, ``:sun:`` for a pictogram, or one
    character the drum has; anything else shows as a blank tile.
    """
    out: list[str] = []
    for match in _TILE.finditer(text):
        colour, name, source = match.group(1), match.group(2), match.group(0)
        if colour:
            out.append(f"{{{colour.lower()}}}")
            continue
        icon = name.lower() if name else EMOJI.get(source.replace("\ufe0f", ""))
        if icon in ICON_NAMES:
            out.append(f":{icon}:")
        elif name:
            # Not a pictogram: the TV shows it as typed.
            out += [":", *parse(source[1:])]
        else:
            char = ALIASES.get(source) or source.upper()
            out.append(char if char in CHARACTERS else " ")
    return out


def tiles(text: str) -> int:
    """Return how many tiles ``text`` takes on the board."""
    return len(parse(text))


def wrap(text: str, width: int = COLS) -> list[str]:
    """Break ``text`` into rows of at most ``width`` tiles, as the TV does."""
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            candidate = f"{line} {word}" if line else word
            if tiles(candidate) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
            line = word
            while tiles(line) > width:
                parts = parse(line)
                lines.append("".join(parts[:width]))
                line = "".join(parts[width:])
        lines.append(line)
    return lines


def rows_needed(text: str) -> int:
    """Return how many rows ``text`` fills on the board."""
    return len(wrap(text))


def board_rows(text: str) -> list[list[str]]:
    """Return the symbols on every tile, row by row, as message() in flaptext.js draws ``text``.

    The rows that fit are centred on the board, and each row in it.
    """
    lines = wrap(text)[:ROWS]
    top = (ROWS - len(lines)) // 2
    rows = []
    for r in range(ROWS):
        line = lines[r - top] if 0 <= r - top < len(lines) else ""
        symbols = parse(line)[:COLS]
        left = (COLS - len(symbols)) // 2
        rows.append([" "] * left + symbols + [" "] * (COLS - left - len(symbols)))
    return rows


class Tile(NamedTuple):
    """One tile as a page draws it: a character, a colour or a pictogram."""

    char: str = ""
    colour: str = ""
    icon: str = ""


def tile(symbol: str) -> Tile:
    """Return the tile that shows ``symbol``, as parse() gives it."""
    if symbol.startswith("{"):
        return Tile(colour=symbol[1])
    if len(symbol) > 1:
        return Tile(icon=symbol[1:-1])
    return Tile(char=symbol.strip())


def board_tiles(text: str) -> list[Tile]:
    """Return every tile on the board showing ``text``, row by row."""
    return [tile(symbol) for row in board_rows(text) for symbol in row]

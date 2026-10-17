"""How a message lays out on the board's tiles, mirroring static/js/splitflap.js.

The TV wraps a message into rows of ``COLS`` tiles and shows ``ROWS`` of
them. The server wraps it the same way so a message that won't fit is
refused when it's posted, rather than losing its tail on the TV.
"""

from __future__ import annotations

import re

COLS = 22
ROWS = 6

# The pictograms the board can draw, as :name: (ICONS in splitflap.js).
ICON_NAMES = frozenset(
    [
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
    ]
)

# One tile each: a colour code, a :name:, an emoji (with its variation
# selector) or any other single character. Python's re has no
# \p{Extended_Pictographic}, so the emoji blocks stand in for it.
_TILE = re.compile(
    r"\{([roygbvw])\}|:([a-z]+):"
    r"|[\u2190-\u21ff\u2300-\u23ff\u2600-\u27bf\u2b00-\u2bff\U0001f000-\U0001faff]\ufe0f?"
    r"|.",
    re.IGNORECASE | re.DOTALL,
)


def _parse(text: str) -> list[str]:
    """Split ``text`` into the source of each tile, as parse() in splitflap.js."""
    out: list[str] = []
    for match in _TILE.finditer(text):
        name = match.group(2)
        if name and name.lower() not in ICON_NAMES:
            # Not a pictogram: the TV shows it as typed.
            out += [":", *_parse(match.group(0)[1:])]
        else:
            out.append(match.group(0))
    return out


def parse(text: str) -> list[str]:
    """Return the source of each tile ``text`` takes: a character, {x} or :name:."""
    return _parse(text)


def tiles(text: str) -> int:
    """Return how many tiles ``text`` takes on the board."""
    return len(_parse(text))


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
                parts = _parse(line)
                lines.append("".join(parts[:width]))
                line = "".join(parts[width:])
        lines.append(line)
    return lines


def rows_needed(text: str) -> int:
    """Return how many rows ``text`` fills on the board."""
    return len(wrap(text))

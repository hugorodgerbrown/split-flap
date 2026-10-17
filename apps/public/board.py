"""The board the front page shows: the real board, flipping through demo messages.

DESIGN.md's front page shows the product, never a picture of it, so the
hero is the board itself (static/css/board.css) with demo content. The
server draws the first message, so the page works without JavaScript;
static/js/front_board.js flips through the rest. Demo data, not live data:
a feed can be empty or wrong, and these never go stale.
"""

import json
import logging
import re
from typing import Any

from apps.boards.layout import COLS, ROWS, parse

logger = logging.getLogger(__name__)

STRIPE = "{r}{o}{y}{g}{b}{v}"

# (the name engraved under the board, its six rows). A row is centred
# unless it holds a tab, which pushes what follows it to the right edge.
DEMO_BOARDS: list[tuple[str, list[str]]] = [
    (
        "Morning",
        [STRIPE, "", "GOOD MORNING", "BINS GO OUT TONIGHT", "", "POSTED BY CLAUDE 07:00"],
    ),
    (
        "Weather",
        [
            "LONDON\tTODAY",
            "",
            "NOW 14°\tPART CLOUDY",
            "HIGH 16°\tLOW 9°",
            "RAIN AFTER 3PM\t{b}",
            "",
        ],
    ),
    (
        "Trains",
        [
            "KINGS CROSS\t07:45",
            "07:52 CAMBRIDGE\t9 {g}",
            "08:04 YORK\t4 {g}",
            "08:15 LEEDS\t1 {y}",
            "08:30 EDINBURGH\t2 {g}",
            "{g} ON TIME  {y} DELAYED",
        ],
    ),
]


def lay_out(row: str) -> list[str]:
    """Return the ``COLS`` tile sources of one row: centred, or spread at a tab."""
    if "\t" in row:
        left, right = (parse(part) for part in row.split("\t", 1))
        tiles = left + [" "] * (COLS - len(left) - len(right)) + right
    else:
        tiles = parse(row)
        tiles = [" "] * ((COLS - len(tiles)) // 2) + tiles
    tiles = [tile if len(tile) > 1 else tile.upper() for tile in tiles[:COLS]]
    return tiles + [" "] * (COLS - len(tiles))


def frames() -> list[list[str]]:
    """Return each demo board as ``ROWS * COLS`` tile sources, row by row."""
    return [[tile for row in rows[:ROWS] for tile in lay_out(row)] for _name, rows in DEMO_BOARDS]


def as_text(rows: list[str]) -> str:
    """Return a board's rows as a sentence a screen reader can say."""
    words = re.sub(r"\{[a-z]\}", " ", " ".join(rows)).split()
    return " ".join(words).capitalize()


def cell(source: str) -> dict[str, str]:
    """Return how one tile draws: a colour (``tile``) or a character (``char``)."""
    if len(source) == 3 and source[0] == "{":
        return {"tile": source[1], "char": ""}
    return {"tile": "", "char": source}


def front_board() -> dict[str, Any]:
    """Return what the front page's board needs: the first board drawn, and all of them."""
    all_frames = frames()
    names = [name for name, _rows in DEMO_BOARDS]
    return {
        "name": names[0],
        "names": names,
        "label": as_text(DEMO_BOARDS[0][1]),
        "cells": [cell(source) for source in all_frames[0]],
        "frames_json": json.dumps(all_frames, ensure_ascii=False),
        "names_json": json.dumps(names),
        "labels_json": json.dumps([as_text(rows) for _name, rows in DEMO_BOARDS]),
    }

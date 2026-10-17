"""Tests for apps.boards.layout: the server wraps messages as the TV does."""

import json
import re
from pathlib import Path

import pytest

from apps.boards.layout import (
    ALIASES,
    CHARACTERS,
    COLS,
    EMOJI,
    PICTOGRAMS,
    ROWS,
    Tile,
    board_rows,
    board_tiles,
    rows_needed,
    tiles,
    wrap,
)

ROOT = Path(__file__).resolve().parents[2]
FLAPTEXT_JS = (ROOT / "static" / "js" / "flaptext.js").read_text()
CASES = json.loads((Path(__file__).parent / "layout_cases.json").read_text())["cases"]


def js_block(name: str) -> str:
    """The body of ``const name = {...};`` in flaptext.js."""
    start = FLAPTEXT_JS.index(f"const {name} = {{")
    return FLAPTEXT_JS[start : FLAPTEXT_JS.index("};", start)]


def test_pictograms_match_the_board() -> None:
    """PICTOGRAMS lists the pictograms flaptext.js draws, in its order."""
    names = re.findall(r"^\s+([a-z]+):", js_block("ICONS"), re.MULTILINE)
    assert tuple(names) == PICTOGRAMS
    assert f"const COLS = {COLS}, ROWS = {ROWS};" in FLAPTEXT_JS


def test_the_tables_match_the_board() -> None:
    """The emoji, the typographic marks and the drum's characters are flaptext.js's."""
    entry = r"'([^']+)':\s*(['\"])(.+?)\2"
    assert {k: v for k, _, v in re.findall(entry, js_block("EMOJI"))} == EMOJI
    assert {k: v for k, _, v in re.findall(entry, js_block("ALIASES"))} == ALIASES
    drum = FLAPTEXT_JS[FLAPTEXT_JS.index("const DRUM = [") :].split("\n")[0]
    spreads = re.findall(r"\.\.\.'((?:[^'\\]|\\.)*)'", drum)
    assert {" "} | set("".join(spreads).replace("\\'", "'")) == CHARACTERS


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["text"][:24] or "empty")
def test_board_rows_draw_as_the_board_does(case: dict[str, object]) -> None:
    """The server draws each sample message tile for tile as flaptext.js does."""
    assert ["|".join(row) for row in board_rows(str(case["text"]))] == case["rows"]


def test_board_tiles_say_what_each_tile_shows() -> None:
    """Each tile is a character, a colour or a pictogram, row by row."""
    drawn = board_tiles("{r}A:sun:")
    assert len(drawn) == COLS * ROWS
    start = (ROWS - 1) // 2 * COLS + (COLS - 3) // 2 - 1  # the blank before the centred three
    assert drawn[start : start + 4] == [
        Tile(),
        Tile(colour="r"),
        Tile(char="A"),
        Tile(icon="sun"),
    ]


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("HELLO", 5),
        ("{r}{g}", 2),
        (":sun: ok", 4),
        (":nope:", 6),
        ("☀️🚆", 2),
        ("", 0),
    ],
)
def test_tiles(text: str, count: int) -> None:
    """Colour codes, known :names: and emoji take one tile; anything else, one per character."""
    assert tiles(text) == count


def test_wrap_breaks_on_words_and_newlines() -> None:
    """Words move to the next row whole; a newline starts a new row."""
    assert wrap("the quick brown fox jumps over\nthe dog") == [
        "the quick brown fox",
        "jumps over",
        "the dog",
    ]


def test_wrap_splits_a_word_longer_than_a_row() -> None:
    """A word wider than the board is cut into rows of COLS tiles."""
    assert wrap("x" * 30) == ["X" * COLS, "X" * 8]


def test_rows_needed_counts_the_seventh_row() -> None:
    """133 characters of words fill seven rows, one more than the board has."""
    text = " ".join(["abcdefghij"] * 13)[:133]
    assert rows_needed(text) == ROWS + 1

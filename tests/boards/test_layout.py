"""Tests for apps.boards.layout: the server wraps messages as the TV does."""

import re
from pathlib import Path

import pytest

from apps.boards.layout import COLS, ICON_NAMES, ROWS, rows_needed, tiles, wrap

SPLITFLAP_JS = Path(__file__).resolve().parents[2] / "static" / "js" / "splitflap.js"


def test_icon_names_match_the_board() -> None:
    """ICON_NAMES lists exactly the pictograms splitflap.js can draw."""
    source = SPLITFLAP_JS.read_text()
    block = source[
        source.index("const ICONS = {") : source.index("};", source.index("const ICONS"))
    ]
    assert set(re.findall(r"^\s+([a-z]+):", block, re.MULTILINE)) == ICON_NAMES
    assert f"const COLS = {COLS}, ROWS = {ROWS};" in source


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
    assert wrap("x" * 30) == ["x" * COLS, "x" * 8]


def test_rows_needed_counts_the_seventh_row() -> None:
    """133 characters of words fill seven rows, one more than the board has."""
    text = " ".join(["abcdefghij"] * 13)[:133]
    assert rows_needed(text) == ROWS + 1

"""Tests for apps.public.board: the demo boards the front page flips through."""

import json
import re
from pathlib import Path

import pytest

from apps.boards.layout import COLS, ICON_NAMES, ROWS, tiles
from apps.public import board

FLAPTEXT_JS = Path(__file__).resolve().parents[2] / "static" / "js" / "flaptext.js"


@pytest.mark.parametrize(("name", "rows"), board.DEMO_BOARDS, ids=lambda v: str(v)[:12])
def test_every_demo_row_fits(name: str, rows: list[str]) -> None:
    """Six rows, none wider than the board, so nothing is cut off."""
    assert len(rows) == ROWS
    for row in rows:
        assert tiles(row.replace("\t", " ")) <= COLS, row


def test_frames_are_whole_boards() -> None:
    """Every frame is ROWS * COLS tiles, each one the drum can show."""
    drum_source = FLAPTEXT_JS.read_text()
    for frame in board.frames():
        assert len(frame) == ROWS * COLS
        for tile in frame:
            assert (
                re.fullmatch(r"\{[roygbvw]\}", tile)
                or tile.strip(":") in ICON_NAMES
                or (len(tile) == 1 and tile in drum_source)
            ), tile


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("HI", " " * 10 + "HI" + " " * 10),
        ("A\tB", "A" + " " * 20 + "B"),
        ("hi", " " * 10 + "HI" + " " * 10),
    ],
)
def test_lay_out_centres_or_spreads(row: str, expected: str) -> None:
    """A row is centred, or spread to both edges at a tab, and shown in capitals."""
    assert "".join(board.lay_out(row)) == expected


def test_lay_out_keeps_colour_tiles_whole() -> None:
    """A colour code is one tile, not three characters."""
    laid = board.lay_out("{r}{g}")
    assert len(laid) == COLS
    assert laid[10:12] == ["{r}", "{g}"]


def test_front_board_draws_the_first_and_carries_the_rest() -> None:
    """The first board as cells; every board, name and label as JSON for the script."""
    data = board.front_board()
    assert data["name"] == board.DEMO_BOARDS[0][0]
    assert len(data["cells"]) == ROWS * COLS
    assert {"tile": "r", "char": "", "icon": ""} in data["cells"]
    assert {"tile": "", "char": "", "icon": "sun"} in data["cells"]
    assert data["pictograms"].endswith("img/pictograms.svg")
    assert len(json.loads(data["frames_json"])) == len(board.DEMO_BOARDS)
    assert json.loads(data["names_json"]) == [name for name, _rows in board.DEMO_BOARDS]
    labels = json.loads(data["labels_json"])
    assert labels[0] == data["label"]
    assert all("{" not in label and "\t" not in label for label in labels)


def test_a_pictogram_is_one_tile() -> None:
    """A pictogram's name is one tile, drawn as its icon."""
    laid = board.lay_out(":sun: 18C")
    assert ":sun:" in laid
    assert board.cell(":sun:") == {"tile": "", "char": "", "icon": "sun"}


def test_a_label_says_a_pictogram_by_name() -> None:
    """A screen reader hears the pictogram's name, not its colons."""
    assert board.as_text([":sun: 18C", "{r}HI"]) == "Sun 18c hi"

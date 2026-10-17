"""The design page and the board tuning page.

The design page shows every token and every component state drawn by
app.css. The board tuning page (boards/tuning.html, as it draws the board
with board.css) tunes the board's motion by eye. They are for the people
building the app, so only staff see them; anyone else gets a 404, as if
they weren't there.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.design import stylesheet
from apps.public.board import DEMO_BOARDS, lay_out

logger = logging.getLogger(__name__)

FAMILY_ORDER = ("colour", "type", "space", "radius", "shadow", "other")


@require_GET
@login_required
def design(request: HttpRequest) -> HttpResponse:
    """The design system, read from the stylesheet so it can't drift from it."""
    if not request.user.is_staff:
        raise Http404
    found = stylesheet.tokens(stylesheet.read())
    families = {
        family: [t for t in found.values() if t.family == family] for family in FAMILY_ORDER
    }
    return render(request, "design/index.html", {"families": families})


# The tuning page's sliders: (TUNING key in static/js/flapmotion.js, label,
# min, max, step, unit). The page reads each starting value from TUNING.
TUNING_SLIDERS: list[tuple[str, str, float, float, float, str]] = [
    ("colMs", "Delay per column", 0, 200, 5, "ms"),
    ("rowMs", "Delay per row", 0, 600, 10, "ms"),
    ("scatterMs", "Random start scatter", 0, 200, 5, "ms"),
    ("spinCap", "Most flaps per tile", 1, 30, 1, "flaps"),
    ("flapMs", "Flap length", 20, 200, 2, "ms"),
    ("flapSpreadMs", "Flap length spread", 0, 100, 2, "ms"),
    ("topShare", "Top leaf share of a flap", 0.2, 0.8, 0.01, ""),
    ("bounceDeg", "Landing bounce", 0, 30, 1, "°"),
]


def tuning_boards() -> list[dict[str, object]]:
    """Return the boards to change between: blank, then the front page's demo boards."""
    boards: list[dict[str, object]] = [{"name": "Blank", "lines": [""] * len(DEMO_BOARDS[0][1])}]
    for name, rows in DEMO_BOARDS:
        boards.append({"name": name, "lines": ["".join(lay_out(row)) for row in rows]})
    return boards


@require_GET
@login_required
def board_tuning(request: HttpRequest) -> HttpResponse:
    """A live board with sliders for every number that shapes its motion."""
    if not request.user.is_staff:
        raise Http404
    boards = tuning_boards()
    return render(
        request,
        "boards/tuning.html",
        {"sliders": TUNING_SLIDERS, "boards": boards, "boards_json": json.dumps(boards)},
    )

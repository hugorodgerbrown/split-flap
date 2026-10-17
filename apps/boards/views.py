"""Views for the display: the TV's board and state, and the signed-in pages.

The TV's two views need no sign-in: the display's uuid in the address is
the secret, so anyone with the link can watch the board but nobody can
change it from there. The signed-in pages show the display and its boards,
and every change to them is a plain form post, so they work without script.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse, HttpResponseNotModified, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.boards.forms import BoardNameForm, MessageForm, SoundDelayForm, SoundForm
from apps.boards.layout import COLOURS, PICTOGRAMS, Tile, board_tiles
from apps.boards.models import (
    MAX_BOARDS,
    MAX_MESSAGE_LENGTH,
    MAX_SOUND_DELAY_MS,
    SOUND_DELAY_STEP_MS,
    Board,
    Display,
)
from apps.boards.services import (
    BoardError,
    add_board,
    delete_board,
    display_for,
    post_message,
    replay,
    set_sound,
    set_sound_delay,
)
from apps.core.decorators import signed_in_user
from apps.public.connector import mcp_url

# How often the TV asks for new content, in seconds.
POLL_SECONDS = 5

# The pictograms drawn for the app's pages, one <symbol> each.
PICTOGRAMS_SVG = "img/pictograms.svg"

# How a pictogram is read out where its name alone wouldn't say.
PICTOGRAM_LABELS = {
    "partcloud": "Sun and cloud",
    "up": "Arrow up",
    "down": "Arrow down",
    "left": "Arrow left",
    "right": "Arrow right",
}

# The board page's palette: every colour tile, then every pictogram, each
# with the code it adds to a message and a name to read out.
PALETTE = [
    {"code": f"{{{letter}}}", "tile": Tile(colour=letter), "label": f"{name} tile"}
    for letter, name in COLOURS.items()
] + [
    {
        "code": f":{name}:",
        "tile": Tile(icon=name),
        "label": PICTOGRAM_LABELS.get(name, name.capitalize()),
    }
    for name in PICTOGRAMS
]


def _display(display_uuid: UUID) -> Display:
    """Return the display with this uuid and its boards, or 404."""
    return get_object_or_404(Display.objects.prefetch_related("boards"), uuid=display_uuid)


@require_GET
def tv(request: HttpRequest, display_uuid: UUID) -> HttpResponse:
    """The board the TV shows, full screen."""
    display = _display(display_uuid)
    return render(
        request,
        "boards/tv.html",
        {
            "display": display,
            "state_url": reverse("tv:state", args=[display.uuid]),
            "poll_seconds": POLL_SECONDS,
        },
    )


@require_GET
def tv_state(request: HttpRequest, display_uuid: UUID) -> HttpResponse:
    """What every board shows, as JSON. Answers 304 while nothing has changed."""
    state = _display(display_uuid).state()
    etag = f'"{state["version"]}"'
    if request.headers.get("If-None-Match") == etag:
        response: HttpResponse = HttpResponseNotModified()
    else:
        response = JsonResponse(state)
    response["ETag"] = etag
    response["Cache-Control"] = "no-cache"
    return response


def _board(request: HttpRequest, board_uuid: UUID) -> Board:
    """Return the signed-in user's board with this uuid, or 404."""
    boards = Board.objects.for_user(signed_in_user(request)).select_related("display")
    return get_object_or_404(boards, uuid=board_uuid)


def _drawing(board: Board) -> dict[str, object]:
    """Return what a page needs to draw ``board`` as the TV shows it."""
    shows = board.message or board.name
    return {"shows": shows, "tiles": board_tiles(shows), "pictograms": static(PICTOGRAMS_SVG)}


def _manage_url(board: object = None, anchor: str = "") -> str:
    """Return the display page's address, with ``board`` selected and ``anchor`` on the end."""
    query = f"?{urlencode({'board': board})}" if board else ""
    return reverse("boards:manage") + query + anchor


def _manage(
    request: HttpRequest,
    display: Display,
    *,
    selected: object = None,
    add_form: BoardNameForm | None = None,
    message_form: MessageForm | None = None,
    status: int = 200,
) -> HttpResponse:
    """Render the display page with one board selected: ``selected``, ``?board=``, or the first.

    The selected board is drawn, with its editor below; any form that
    failed is shown in place of a fresh one.
    """
    boards = list(display.boards.all())
    wanted = str(selected or request.GET.get("board", ""))
    board = next((b for b in boards if str(b.uuid) == wanted), boards[0])
    return render(
        request,
        "boards/manage.html",
        {
            "display": display,
            "boards": boards,
            "board": board,
            **_drawing(board),
            "message_form": message_form or MessageForm(initial={"text": board.message}),
            "palette": PALETTE,
            "max_message_length": MAX_MESSAGE_LENGTH,
            "tv_url": request.build_absolute_uri(reverse("tv:board", args=[display.uuid])),
            "state_url": reverse("tv:state", args=[display.uuid]),
            "poll_seconds": POLL_SECONDS,
            "mcp_url": mcp_url(),
            "form": add_form or BoardNameForm(display),
            "max_boards": MAX_BOARDS,
            # The Sound timing stepper's two buttons post the next step either way.
            "delay_less": max(display.sound_delay_ms - SOUND_DELAY_STEP_MS, 0),
            "delay_more": min(display.sound_delay_ms + SOUND_DELAY_STEP_MS, MAX_SOUND_DELAY_MS),
        },
        status=status,
    )


def _htmx_login_required(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Like ``login_required``, but sends a signed-out htmx request to sign-in.

    The display page swaps parts of itself from the response: the controls,
    or the board, editor and list when you pick a board or Save. Followed as
    a redirect, the sign-in page has none of them, so the swap would empty
    them; an ``HX-Redirect`` makes htmx load the sign-in page instead.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        back = request.get_full_path() if request.method == "GET" else reverse("boards:manage")
        sign_in = redirect_to_login(back)
        if request.headers.get("HX-Request") != "true":
            return sign_in
        return HttpResponse(status=204, headers={"HX-Redirect": sign_in["Location"]})

    return wrapper


@require_GET
@_htmx_login_required
def display_manage(request: HttpRequest) -> HttpResponse:
    """The display page: the selected board and its editor, the display's links, and its boards."""
    return _manage(request, display_for(signed_in_user(request)))


@require_POST
@_htmx_login_required
def display_sound(request: HttpRequest) -> HttpResponse:
    """Turn the display's flap sound on or off."""
    display = display_for(signed_in_user(request))
    form = SoundForm(request.POST)
    if form.is_valid():
        set_sound(display, form.on())
    return redirect(_manage_url(request.POST.get("board"), "#sound"))


@require_POST
@_htmx_login_required
def display_sound_delay(request: HttpRequest) -> HttpResponse:
    """Set how long the display holds its flaps back for the sound."""
    display = display_for(signed_in_user(request))
    form = SoundDelayForm(request.POST)
    if form.is_valid():
        set_sound_delay(display, form.cleaned_data["sound_delay_ms"])
    return redirect(_manage_url(request.POST.get("board"), "#sound-timing"))


@require_POST
@_htmx_login_required
def display_replay(request: HttpRequest) -> HttpResponse:
    """Have the display flip its board again, without changing the message."""
    replay(display_for(signed_in_user(request)))
    return redirect(_manage_url(request.POST.get("board"), "#replay"))


@require_POST
@login_required
def board_add(request: HttpRequest) -> HttpResponse:
    """Add a board to the end of the signed-in user's display."""
    display = display_for(signed_in_user(request))
    form = BoardNameForm(display, request.POST)
    if form.is_valid():
        try:
            board = add_board(display, form.cleaned_data["name"])
        except BoardError as error:
            form.add_error("name", str(error))
        else:
            return redirect(_manage_url(board.uuid))
    return _manage(request, display, add_form=form, status=400)


@require_GET
@login_required
def board_detail(request: HttpRequest, board_uuid: UUID) -> HttpResponse:
    """A board's old page: its editor is on the display page now, so go there."""
    return redirect(_manage_url(_board(request, board_uuid).uuid))


@require_POST
@_htmx_login_required
def board_message(request: HttpRequest, board_uuid: UUID) -> HttpResponse:
    """Put a new message on a board, or clear it."""
    board = _board(request, board_uuid)
    form = MessageForm({"text": ""} if "clear" in request.POST else request.POST)
    if not form.is_valid():
        return _manage(request, board.display, selected=board.uuid, message_form=form, status=400)
    post_message(board.display, form.cleaned_data["text"], board.name)
    return redirect(_manage_url(board.uuid))


@require_http_methods(["GET", "POST"])
@login_required
def board_delete(request: HttpRequest, board_uuid: UUID) -> HttpResponse:
    """Ask before deleting a board, then delete it."""
    board = _board(request, board_uuid)
    error = ""
    if request.method == "POST":
        try:
            delete_board(board)
        except BoardError as refused:
            error = str(refused)
        else:
            return redirect("boards:manage")
    is_last = not Board.objects.filter(display_id=board.display_id).exclude(pk=board.pk).exists()
    return render(
        request,
        "boards/delete.html",
        {"board": board, "is_last": is_last, "error": error},
        status=400 if error else 200,
    )

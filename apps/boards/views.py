"""Views for the display: the TV's board and state, and the signed-in page.

The TV's two views need no sign-in: the display's uuid in the address is
the secret, so anyone with the link can watch the board but nobody can
change it from there.
"""

from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotModified, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.boards.forms import PostMessageForm
from apps.boards.models import Display
from apps.boards.services import display_for, post_message
from apps.core.decorators import signed_in_user

# How often the TV asks for new content, in seconds.
POLL_SECONDS = 5


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


def _manage(
    request: HttpRequest, display: Display, form: PostMessageForm, status: int = 200
) -> HttpResponse:
    """Render the signed-in display page."""
    return render(
        request,
        "boards/manage.html",
        {
            "display": display,
            "boards": display.boards.all(),
            "tv_url": request.build_absolute_uri(reverse("tv:board", args=[display.uuid])),
            "form": form,
        },
        status=status,
    )


@require_GET
@login_required
def display_manage(request: HttpRequest) -> HttpResponse:
    """The signed-in page: the TV's link and a form to post to a board."""
    return _manage(request, display_for(signed_in_user(request)), PostMessageForm())


@require_POST
@login_required
def display_post(request: HttpRequest) -> HttpResponse:
    """Post a message to one of the signed-in user's boards."""
    display = display_for(signed_in_user(request))
    form = PostMessageForm(request.POST)
    if not form.is_valid():
        return _manage(request, display, form, status=400)
    post_message(display, form.cleaned_data["text"], form.cleaned_data["kind"])
    return redirect("boards:manage")

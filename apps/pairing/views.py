"""Views for pairing: the TV app's two JSON endpoints and the owner's code page.

The TV's endpoints need no sign-in and carry no cookies, so starting a
pairing is exempt from CSRF: there is no session for a forged request to
ride on, and all it makes is a code that expires in minutes.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.boards.services import display_for
from apps.core.decorators import signed_in_user
from apps.core.ratelimit import client_ip, over_limit
from apps.pairing import services
from apps.pairing.forms import PairForm

# How often the TV asks whether its code has been entered, in seconds.
POLL_SECONDS = 3


def _json(data: dict[str, object], status: int = 200) -> JsonResponse:
    """Return ``data`` as JSON that nothing between here and the TV may keep."""
    response = JsonResponse(data, status=status)
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def tv_start(request: HttpRequest) -> HttpResponse:
    """Start a pairing: the code to show, the link for its QR code and where to poll."""
    if over_limit("pairing-start-ip", client_ip(request), limit=20, window_seconds=3600):
        return _json({"error": "rate_limited"}, status=429)
    started = services.start()
    pair_url = f"{reverse('pairing:pair')}?code={started.code}"
    return _json(
        {
            "code": services.format_code(started.code),
            "pair_url": request.build_absolute_uri(pair_url),
            "poll_url": request.build_absolute_uri(reverse("pairing:poll", args=[started.token])),
            "poll_seconds": POLL_SECONDS,
            "expires_at": started.pairing.expires_at.isoformat(),
        },
        status=201,
    )


@require_GET
def tv_poll(request: HttpRequest, token: str) -> HttpResponse:
    """Tell the TV whether its code has been entered, and if so, its display's link."""
    pairing = services.find(token)
    if pairing is None:
        return _json({"status": "unknown"}, status=404)
    if pairing.claimed_at is None:
        if pairing.is_expired():
            return _json({"status": "expired"}, status=410)
        return _json({"status": "waiting", "expires_at": pairing.expires_at.isoformat()})
    display = services.collect(pairing)
    if display is None:
        return _json({"status": "expired"}, status=410)
    return _json(
        {
            "status": "paired",
            "display_name": display.name,
            "display_url": request.build_absolute_uri(reverse("tv:board", args=[display.uuid])),
        }
    )


@require_http_methods(["GET", "POST"])
@login_required
def pair(request: HttpRequest) -> HttpResponse:
    """The owner's page: type the code the TV shows to put this display on it."""
    user = signed_in_user(request)
    display = display_for(user)
    status = 200
    if request.method == "POST":
        form = PairForm(request.POST)
        if over_limit("pairing-claim-user", str(user.pk), limit=10, window_seconds=600):
            form.add_error(None, "Too many tries. Wait a few minutes, then try again.")
            status = 429
        elif form.is_valid():
            if services.claim(form.cleaned_data["code"], display):
                return redirect(f"{reverse('pairing:pair')}?paired=1")
            form.add_error(
                "code",
                "That code isn't waiting to be linked. Check the TV: codes last "
                f"{services.PAIRING_MINUTES} minutes and work once.",
            )
            status = 400
        else:
            status = 400
    else:
        form = PairForm(initial={"code": request.GET.get("code", "")[:20]})
    return render(
        request,
        "pairing/pair.html",
        {
            "display": display,
            "form": form,
            "paired": request.method == "GET" and request.GET.get("paired") == "1",
        },
        status=status,
    )

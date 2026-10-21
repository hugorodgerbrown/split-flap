"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import admin_login
from apps.core.views import healthz, livez
from apps.mcp.views import mcp, openai_apps_challenge
from apps.pwa.conf import APP_NAME

admin.site.site_header = APP_NAME
admin.site.site_title = APP_NAME

urlpatterns = [
    # Public: the homepage, terms, privacy, and signing in and out.
    path("", include("apps.public.urls")),
    path("", include("apps.accounts.urls")),
    # Health checks: /livez for Render (process up), /healthz adds the database.
    path("livez", livez, name="livez"),
    path("healthz", healthz, name="healthz"),
    # Staff sign in like everyone else; the admin's password form is unused.
    path("admin/login/", admin_login),
    path("admin/", admin.site.urls),
    # The installed app: everything under /app/ (apps/pwa/conf.py: SCOPE).
    path("app/", include("apps.pwa.urls")),
    path("app/", include("apps.notes.urls")),
    path("app/", include("apps.boards.urls")),
    # The TV: a display's board and its state, by the display's secret uuid.
    path("d/", include("apps.boards.tv_urls")),
    # Linking a TV app to a display by code: /d/pair/ for the TV, /app/display/pair/.
    path("", include("apps.pairing.urls")),
    path("app/", include("apps.design.urls")),
    path("", include("mcp_auth.urls")),
    path("mcp", mcp, name="mcp"),
    # OpenAI's domain check for ChatGPT's app directory.
    path(".well-known/openai-apps-challenge", openai_apps_challenge, name="openai-apps-challenge"),
]

# The error pages (apps/core/errors.py): JSON, plain text for htmx, or HTML.
handler400 = "apps.core.errors.bad_request"
handler403 = "apps.core.errors.permission_denied"
handler404 = "apps.core.errors.page_not_found"
handler500 = "apps.core.errors.server_error"

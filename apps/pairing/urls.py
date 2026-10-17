"""URLs for pairing: the TV app's endpoints under /d/pair/, the owner's page under /app/."""

from django.urls import path

from apps.pairing import views

app_name = "pairing"

urlpatterns = [
    path("d/pair/", views.tv_start, name="start"),
    path("d/pair/<str:token>/", views.tv_poll, name="poll"),
    path("app/display/pair/", views.pair, name="pair"),
]

"""URLs for the TV: the board itself and the state it polls, at /d/<uuid>/."""

from django.urls import path

from apps.boards import views

app_name = "tv"

urlpatterns = [
    path("<uuid:display_uuid>/", views.tv, name="board"),
    path("<uuid:display_uuid>/state.json", views.tv_state, name="state"),
]

"""URLs for the signed-in display page and its boards' pages, under /app/."""

from django.urls import path

from apps.boards import views

app_name = "boards"

urlpatterns = [
    path("display/", views.display_manage, name="manage"),
    path("display/sound/", views.display_sound, name="sound"),
    path("display/sound/timing/", views.display_sound_delay, name="sound_delay"),
    path("display/replay/", views.display_replay, name="replay"),
    path("display/boards/", views.board_add, name="add"),
    path("display/boards/<uuid:board_uuid>/", views.board_detail, name="board"),
    path("display/boards/<uuid:board_uuid>/message/", views.board_message, name="message"),
    path("display/boards/<uuid:board_uuid>/delete/", views.board_delete, name="delete"),
]

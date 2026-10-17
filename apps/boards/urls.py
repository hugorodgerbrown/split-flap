"""URLs for the signed-in display page and its boards' pages, under /app/."""

from django.urls import path

from apps.boards import views

app_name = "boards"

urlpatterns = [
    path("display/", views.display_manage, name="manage"),
    path("display/boards/", views.board_add, name="add"),
    path("display/boards/<uuid:board_uuid>/", views.board_detail, name="board"),
    path("display/boards/<uuid:board_uuid>/message/", views.board_message, name="message"),
    path("display/boards/<uuid:board_uuid>/name/", views.board_rename, name="rename"),
    path("display/boards/<uuid:board_uuid>/move/", views.board_move, name="move"),
    path("display/boards/<uuid:board_uuid>/delete/", views.board_delete, name="delete"),
]

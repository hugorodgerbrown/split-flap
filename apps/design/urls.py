"""URLs for the design page and the board tuning page."""

from django.urls import path

from apps.design import views

app_name = "design"

urlpatterns = [
    path("design/", views.design, name="index"),
    path("design/board/", views.board_tuning, name="board"),
]

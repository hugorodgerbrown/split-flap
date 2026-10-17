"""URLs for the signed-in display page, under /app/."""

from django.urls import path

from apps.boards import views

app_name = "boards"

urlpatterns = [
    path("display/", views.display_manage, name="manage"),
    path("display/post/", views.display_post, name="post"),
]

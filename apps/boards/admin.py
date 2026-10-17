"""Admin for displays and boards."""

from django.contrib import admin

from apps.boards.models import Board, Display


class BoardInline(admin.TabularInline):
    """A display's boards, edited with it."""

    model = Board
    extra = 0
    fields = ("kind", "position", "message", "posted_at")
    readonly_fields = ("posted_at",)


@admin.register(Display)
class DisplayAdmin(admin.ModelAdmin):
    """Displays, oldest first, with their boards."""

    list_display = ("to_string", "owner", "uuid", "created_at")
    list_select_related = ("owner",)
    readonly_fields = ("uuid",)
    inlines = [BoardInline]

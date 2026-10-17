"""Boards are named screens that show what they're given, not fixed kinds.

Each existing board keeps its place and is named after its old kind, so a
display that had Custom, News, Weather and Travel still has those four.
"""

import django.db.models.functions.text
from django.db import migrations, models

NAMES = {"custom": "Custom", "news": "News", "weather": "Weather", "travel": "Travel"}


def name_boards(apps, schema_editor):
    """Name each board after the kind it had."""
    Board = apps.get_model("boards", "Board")
    for board in Board.objects.all():
        board.name = NAMES.get(board.kind, board.kind.title())
        board.save(update_fields=["name"])


class Migration(migrations.Migration):
    """Swap a board's kind for a name unique on its display."""

    dependencies = [
        ("boards", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="board",
            name="name",
            field=models.CharField(default="", max_length=40),
            preserve_default=False,
        ),
        migrations.RunPython(name_boards, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="board",
            name="one_board_per_kind",
        ),
        migrations.RemoveField(
            model_name="board",
            name="kind",
        ),
        migrations.AddConstraint(
            model_name="board",
            constraint=models.UniqueConstraint(
                models.F("display"),
                django.db.models.functions.text.Lower("name"),
                name="one_board_per_name",
            ),
        ),
    ]

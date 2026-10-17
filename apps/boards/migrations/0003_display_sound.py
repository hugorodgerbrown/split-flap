"""A display remembers whether its flap sound is on; it starts off."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("boards", "0002_boards_have_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="display",
            name="sound",
            field=models.BooleanField(default=False),
        ),
    ]

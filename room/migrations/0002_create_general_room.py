from django.db import migrations


def create_general_room(apps, schema_editor):
    """Create a default room so the app is usable right after `migrate`."""
    Room = apps.get_model("room", "Room")
    Room.objects.get_or_create(slug="general", defaults={"name": "General"})


class Migration(migrations.Migration):
    dependencies = [
        ("room", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_general_room, migrations.RunPython.noop),
    ]

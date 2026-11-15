from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("waterbodies", "0005_waterbodymap_game_coordinates")]

    operations = [
        migrations.RemoveField(model_name="waterbodymap", name="image_left"),
        migrations.RemoveField(model_name="waterbodymap", name="image_right"),
        migrations.RemoveField(model_name="waterbodymap", name="image_top"),
        migrations.RemoveField(model_name="waterbodymap", name="image_bottom"),
    ]

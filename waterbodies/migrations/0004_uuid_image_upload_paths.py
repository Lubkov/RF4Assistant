from django.db import migrations, models
import waterbodies.upload_paths


class Migration(migrations.Migration):
    dependencies = [("waterbodies", "0003_waterbodymap")]

    operations = [
        migrations.AlterField(
            model_name="waterbody", name="image",
            field=models.ImageField(blank=True, upload_to=waterbodies.upload_paths.waterbody_image_path, verbose_name="Изображение"),
        ),
        migrations.AlterField(
            model_name="waterbodymap", name="image",
            field=models.ImageField(upload_to=waterbodies.upload_paths.waterbody_map_path, verbose_name="Игровая карта"),
        ),
    ]

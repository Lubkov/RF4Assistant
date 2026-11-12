from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("waterbodies", "0002_seed_waterbodies")]

    operations = [
        migrations.CreateModel(
            name="WaterbodyMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="waterbodies/maps/", verbose_name="Игровая карта")),
                ("source_url", models.URLField(blank=True, verbose_name="Источник изображения")),
                ("waterbody", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="game_map", to="waterbodies.waterbody", verbose_name="Водоём",
                )),
            ],
            options={"verbose_name": "Карта водоёма", "verbose_name_plural": "Карты водоёмов"},
        ),
    ]

import django.db.models.deletion
from django.db import migrations, models
import django.core.validators
import fishing_spots.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("waterbodies", "0006_remove_waterbodymap_image_bounds"),
        ("fish", "0004_populate_waterbody_fish_from_records"),
    ]

    operations = [
        migrations.CreateModel(
            name="FishingSpot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("x", models.FloatField(verbose_name="Координата X")),
                ("y", models.FloatField(verbose_name="Координата Y")),
                ("clip", models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name="Клипса")),
                ("depth_cm", models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name="Глубина, см")),
                ("retrieve_speed", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(50)], verbose_name="Скорость проводки")),
                ("is_mixed_fish", models.BooleanField(default=False, verbose_name="Разнорыбица")),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата создания")),
                ("waterbody", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fishing_spots", to="waterbodies.waterbody", verbose_name="Водоём")),
            ],
            options={"verbose_name": "Место ловли", "verbose_name_plural": "Места ловли", "ordering": ("-created_at", "-pk")},
        ),
        migrations.CreateModel(
            name="FishingSpotCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("farm", "Фарм"), ("trophy", "Трофей"), ("qualification", "Квалификация"), ("task", "Задание")], max_length=20, verbose_name="Категория")),
                ("fishing_spot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="categories", to="fishing_spots.fishingspot", verbose_name="Место ловли")),
            ],
            options={"verbose_name": "Категория места ловли", "verbose_name_plural": "Категории мест ловли"},
        ),
        migrations.CreateModel(
            name="FishingSpotFish",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fish", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fishing_spot_links", to="fish.fish", verbose_name="Рыба")),
                ("fishing_spot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="spot_fish", to="fishing_spots.fishingspot", verbose_name="Место ловли")),
            ],
            options={"verbose_name": "Рыба места ловли", "verbose_name_plural": "Рыбы мест ловли"},
        ),
        migrations.AddField(
            model_name="fishingspot", name="fish",
            field=models.ManyToManyField(blank=True, related_name="fishing_spots", through="fishing_spots.FishingSpotFish", to="fish.fish", verbose_name="Виды рыб"),
        ),
        migrations.CreateModel(
            name="FishingSpotScreenshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to=fishing_spots.models.fishing_spot_screenshot_path, verbose_name="Скриншот")),
                ("position", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name="Позиция")),
                ("fishing_spot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="screenshots", to="fishing_spots.fishingspot", verbose_name="Место ловли")),
            ],
            options={"verbose_name": "Скриншот места ловли", "verbose_name_plural": "Скриншоты мест ловли", "ordering": ("position", "pk")},
        ),
        migrations.AddConstraint(model_name="fishingspotcategory", constraint=models.UniqueConstraint(fields=("fishing_spot", "category"), name="unique_fishing_spot_category")),
        migrations.AddConstraint(model_name="fishingspotfish", constraint=models.UniqueConstraint(fields=("fishing_spot", "fish"), name="unique_fishing_spot_fish")),
        migrations.AddConstraint(model_name="fishingspotscreenshot", constraint=models.UniqueConstraint(fields=("fishing_spot", "position"), name="unique_fishing_spot_screenshot_position")),
    ]

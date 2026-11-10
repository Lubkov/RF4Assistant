import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("waterbodies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Fish",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True, verbose_name="Название")),
                ("trophy_weight", models.PositiveIntegerField(verbose_name="Трофейный вес, г")),
                ("super_trophy_weight", models.PositiveIntegerField(blank=True, null=True, verbose_name="Супертрофейный вес, г")),
                ("rarity", models.PositiveSmallIntegerField(choices=[(1, "Обычная"), (2, "Редкая"), (3, "Очень редкая")], default=1, verbose_name="Редкость")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активна")),
            ],
            options={
                "verbose_name": "Рыба",
                "verbose_name_plural": "Рыбы",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="WaterbodyFish",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fish", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="waterbody_fish", to="fish.fish", verbose_name="Рыба")),
                ("waterbody", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="waterbody_fish", to="waterbodies.waterbody", verbose_name="Водоём")),
            ],
            options={
                "verbose_name": "Рыба водоёма",
                "verbose_name_plural": "Рыбы водоёмов",
            },
        ),
        migrations.AddConstraint(
            model_name="waterbodyfish",
            constraint=models.UniqueConstraint(fields=("waterbody", "fish"), name="unique_waterbody_fish"),
        ),
    ]

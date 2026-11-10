from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Waterbody",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="Название")),
                ("level", models.PositiveSmallIntegerField(verbose_name="Уровень доступа")),
                ("slug", models.SlugField(max_length=150, unique=True, verbose_name="URL-идентификатор")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("image", models.ImageField(blank=True, upload_to="waterbodies/", verbose_name="Изображение")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
            ],
            options={
                "verbose_name": "Водоём",
                "verbose_name_plural": "Водоёмы",
                "ordering": ("level", "id"),
            },
        ),
    ]

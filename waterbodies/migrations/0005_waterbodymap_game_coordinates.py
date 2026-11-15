from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("waterbodies", "0004_uuid_image_upload_paths")]
    operations = [
        migrations.AddField(model_name="waterbodymap", name="game_x_min", field=models.FloatField(blank=True, null=True, verbose_name="Игровая координата X слева")),
        migrations.AddField(model_name="waterbodymap", name="game_x_max", field=models.FloatField(blank=True, null=True, verbose_name="Игровая координата X справа")),
        migrations.AddField(model_name="waterbodymap", name="game_y_min", field=models.FloatField(blank=True, null=True, verbose_name="Игровая координата Y снизу")),
        migrations.AddField(model_name="waterbodymap", name="game_y_max", field=models.FloatField(blank=True, null=True, verbose_name="Игровая координата Y сверху")),
        migrations.AddField(model_name="waterbodymap", name="image_left", field=models.FloatField(default=0, verbose_name="Левый край игровой области (0–1)")),
        migrations.AddField(model_name="waterbodymap", name="image_right", field=models.FloatField(default=1, verbose_name="Правый край игровой области (0–1)")),
        migrations.AddField(model_name="waterbodymap", name="image_top", field=models.FloatField(default=0, verbose_name="Верхний край игровой области (0–1)")),
        migrations.AddField(model_name="waterbodymap", name="image_bottom", field=models.FloatField(default=1, verbose_name="Нижний край игровой области (0–1)")),
    ]

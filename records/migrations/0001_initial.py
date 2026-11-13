# Initial records models. Existing Fish and Waterbody tables are NOT renamed.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("fish", "0002_seed_fish"), ("waterbodies", "0004_uuid_image_upload_paths")]
    operations = [
        migrations.CreateModel(name="Collection", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("source_url", models.URLField(max_length=300)),
            ("region", models.CharField(db_index=True, max_length=2)),
            ("record_type", models.CharField(default="weekly", max_length=12)),
            ("collected_at", models.DateTimeField()),
            ("fish_group_count", models.PositiveIntegerField(default=0)),
            ("record_count", models.PositiveIntegerField()),
            ("new_record_count", models.PositiveIntegerField()),
        ], options={"db_table": "records_collections", "ordering": ("-collected_at",), "verbose_name": "Сбор рекордов", "verbose_name_plural": "Сборы рекордов"}),
        migrations.CreateModel(name="Catch", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("fingerprint", models.CharField(max_length=64, unique=True)),
            ("fish_name", models.CharField(max_length=200)),
            ("waterbody_name", models.CharField(max_length=200)),
            ("bait", models.TextField(blank=True)),
            ("weight_g", models.PositiveIntegerField()),
            ("player", models.CharField(max_length=200)),
            ("caught_date", models.DateField(db_index=True)),
            ("first_seen_at", models.DateTimeField()),
            ("last_seen_at", models.DateTimeField()),
            ("fish_icon_url", models.URLField(blank=True, max_length=600)),
            ("bait_icon_url", models.URLField(blank=True, max_length=600)),
            ("collection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="catches", to="records.collection")),
            ("fish", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="record_catches", to="fish.fish", verbose_name="Рыба из справочника")),
            ("waterbody", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="record_catches", to="waterbodies.waterbody", verbose_name="Водоём из справочника")),
        ], options={"db_table": "records_catches", "ordering": ("-caught_date", "-weight_g"), "verbose_name": "Улов", "verbose_name_plural": "Уловы рекордов"}),
        migrations.CreateModel(name="WeeklyCatchRegion", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("region", models.CharField(max_length=2)),
            ("first_seen_at", models.DateTimeField()),
            ("last_seen_at", models.DateTimeField()),
            ("catch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weekly_regions", to="records.catch")),
        ], options={"db_table": "records_weekly_regions", "verbose_name": "Недельный регион улова", "verbose_name_plural": "Недельные регионы уловов"}),
        migrations.AddIndex(model_name="catch", index=models.Index(fields=["waterbody", "caught_date"], name="rec_wb_date_idx")),
        migrations.AddIndex(model_name="catch", index=models.Index(fields=["fish", "caught_date"], name="rec_fish_date_idx")),
        migrations.AddIndex(model_name="weeklycatchregion", index=models.Index(fields=["region", "catch"], name="rec_region_catch_idx")),
        migrations.AddConstraint(model_name="weeklycatchregion", constraint=models.UniqueConstraint(fields=("catch", "region"), name="rec_unique_catch_region")),
    ]

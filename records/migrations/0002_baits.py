import django.db.models.deletion
from django.db import migrations, models


def backfill_baits(apps, schema_editor):
    Bait = apps.get_model("records", "Bait")
    Catch = apps.get_model("records", "Catch")
    db = schema_editor.connection.alias
    existing = {name: pk for pk, name in Bait.objects.using(db).values_list("pk", "name")}
    changes = []
    for catch in Catch.objects.using(db).only("id", "bait").iterator(chunk_size=500):
        parts = [part.strip() for part in (catch.bait or "").split(";") if part.strip()]
        # Preserve unknown raw text; do not make up a third reference.
        if len(parts) > 2:
            continue
        ids = []
        for name in parts:
            pk = existing.get(name)
            if pk is None:
                obj, _ = Bait.objects.using(db).get_or_create(name=name)
                pk = obj.pk
                existing[name] = pk
            ids.append(pk)
        catch.bait1_id = ids[0] if len(ids) > 0 else None
        catch.bait2_id = ids[1] if len(ids) > 1 else None
        changes.append(catch)
        if len(changes) >= 500:
            Catch.objects.using(db).bulk_update(changes, ["bait1", "bait2"])
            changes.clear()
    if changes:
        Catch.objects.using(db).bulk_update(changes, ["bait1", "bait2"])


class Migration(migrations.Migration):
    dependencies = [("records", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="Bait",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True, verbose_name="Название")),
                ("image", models.ImageField(blank=True, upload_to="baits/", verbose_name="Иконка")),
            ],
            options={"db_table": "baits", "ordering": ("name",), "verbose_name": "Наживка", "verbose_name_plural": "Наживки"},
        ),
        migrations.AddField(model_name="catch", name="bait1", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="first_bait_catches", to="records.bait", verbose_name="Первая наживка")),
        migrations.AddField(model_name="catch", name="bait2", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="second_bait_catches", to="records.bait", verbose_name="Вторая наживка")),
        migrations.RunPython(backfill_baits, migrations.RunPython.noop),
    ]

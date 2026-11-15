"""Add known waterbody/fish combinations from imported historical catches."""
from django.db import migrations


def populate_waterbody_fish(apps, schema_editor):
    Catch = apps.get_model("records", "Catch")
    WaterbodyFish = apps.get_model("fish", "WaterbodyFish")
    db = schema_editor.connection.alias

    pairs = (
        Catch.objects.using(db)
        .filter(fish_id__isnull=False, waterbody_id__isnull=False)
        .order_by()
        .values_list("waterbody_id", "fish_id")
        .distinct()
    )
    batch = []
    for waterbody_id, fish_id in pairs.iterator(chunk_size=500):
        batch.append(WaterbodyFish(waterbody_id=waterbody_id, fish_id=fish_id))
        if len(batch) >= 500:
            WaterbodyFish.objects.using(db).bulk_create(batch, ignore_conflicts=True)
            batch.clear()
    if batch:
        WaterbodyFish.objects.using(db).bulk_create(batch, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("fish", "0003_fish_image"),
        ("records", "0002_baits"),
    ]

    operations = [
        migrations.RunPython(populate_waterbody_fish, migrations.RunPython.noop),
    ]

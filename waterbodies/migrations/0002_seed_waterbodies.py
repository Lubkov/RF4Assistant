from django.db import migrations


# IDs, names and levels are imported verbatim from the original Location table.
# Slugs are new stable identifiers reserved for future URLs.
WATERBODIES = [(1, 'оз. Комариное', 1, 'komarinoe'), (2, 'оз. Лосиное', 1, 'losinoe'), (3, 'р. Вьюнок', 1, 'vyunok'), (4, 'оз. Старый Острог', 12, 'stary-ostrog'), (5, 'р. Белая', 12, 'belaya'), (6, 'оз. Куори', 16, 'kuori'), (7, 'оз. Медвежье', 18, 'medvezhye'), (8, 'р. Волхов', 20, 'volkhov'), (9, 'р. Северский Донец', 22, 'seversky-donets'), (10, 'р. Сура', 24, 'sura'), (11, 'Ладожское оз.', 26, 'ladozhskoe-ozero'), (12, 'оз. Янтарное', 26, 'yantarnoe'), (13, 'Ладожский архипелаг', 27, 'ladozhskiy-arkhipelag'), (14, 'р. Ахтуба', 28, 'akhtuba'), (15, 'оз. Медное', 29, 'mednoe'), (16, 'р. Нижняя Тунгуска', 30, 'nizhnyaya-tunguska'), (17, 'р. Яма', 32, 'yama'), (18, 'Норвежское море', 34, 'norvezhskoe-more')]


def seed_waterbodies(apps, schema_editor):
    Waterbody = apps.get_model("waterbodies", "Waterbody")
    database = schema_editor.connection.alias
    Waterbody.objects.using(database).bulk_create(
        [Waterbody(id=pk, name=name, level=level, slug=slug)
         for pk, name, level, slug in WATERBODIES]
    )


class Migration(migrations.Migration):
    dependencies = [("waterbodies", "0001_initial")]

    operations = [
        migrations.RunPython(seed_waterbodies, reverse_code=migrations.RunPython.noop),
    ]

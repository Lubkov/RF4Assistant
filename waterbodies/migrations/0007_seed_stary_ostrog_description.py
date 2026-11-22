from django.db import migrations


DESCRIPTION = (
    "Небольшое, но глубокое озеро, затерянное в болотистых лесах костромской области. "
    "Здешние воды богаты крупной рыбой, среди которой нередко попадается трофейная щука или окунь. "
    "Местные рыболовы рассказывают о поимках чрезвычайно длинных угрей, а некоторые из них вылавливали даже сомов. "
    "Любители фидерной ловли смогут поймать леща, карпа или амура. "
    "Особенно интересен черный амур, который высоко ценится на местном рыбном рынке за свои прекрасные кулинарные качества."
)


def seed_description(apps, schema_editor):
    waterbody = apps.get_model("waterbodies", "Waterbody")
    waterbody.objects.using(schema_editor.connection.alias).filter(
        slug="stary-ostrog", description="",
    ).update(description=DESCRIPTION)


def remove_description(apps, schema_editor):
    waterbody = apps.get_model("waterbodies", "Waterbody")
    waterbody.objects.using(schema_editor.connection.alias).filter(
        slug="stary-ostrog", description=DESCRIPTION,
    ).update(description="")


class Migration(migrations.Migration):
    dependencies = [("waterbodies", "0006_remove_waterbodymap_image_bounds")]

    operations = [migrations.RunPython(seed_description, remove_description)]

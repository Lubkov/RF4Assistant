from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fish", "0002_seed_fish")]
    operations = [
        migrations.AddField(
            model_name="fish", name="image",
            field=models.ImageField(blank=True, upload_to="fish/icons/", verbose_name="Иконка"),
        ),
    ]

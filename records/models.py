from django.db import models


class Collection(models.Model):
    """Only successful imports that introduced at least one new unique catch."""

    source_url = models.URLField(max_length=300)
    region = models.CharField(max_length=2, db_index=True)
    record_type = models.CharField(max_length=12, default="weekly")
    collected_at = models.DateTimeField()
    fish_group_count = models.PositiveIntegerField(default=0)
    record_count = models.PositiveIntegerField()
    new_record_count = models.PositiveIntegerField()

    class Meta:
        db_table = "records_collections"
        ordering = ("-collected_at",)
        verbose_name = "Сбор рекордов"
        verbose_name_plural = "Сборы рекордов"

    def __str__(self):
        return f"{self.region} {self.collected_at:%Y-%m-%d %H:%M} +{self.new_record_count}"


class Bait(models.Model):
    name = models.CharField("Название", max_length=255, unique=True)
    image = models.ImageField("Иконка", upload_to="baits/", blank=True)

    class Meta:
        db_table = "baits"
        ordering = ("name",)
        verbose_name = "Наживка"
        verbose_name_plural = "Наживки"

    def __str__(self):
        return self.name


class Catch(models.Model):
    """A unique, identifiable catch, independent of rating and region."""

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="catches")
    fingerprint = models.CharField(max_length=64, unique=True)
    fish = models.ForeignKey(
        "fish.Fish", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="record_catches", verbose_name="Рыба из справочника",
    )
    waterbody = models.ForeignKey(
        "waterbodies.Waterbody", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="record_catches", verbose_name="Водоём из справочника",
    )
    # Preserve exact source values for unmatched names and historical integrity.
    fish_name = models.CharField(max_length=200)
    waterbody_name = models.CharField(max_length=200)
    bait = models.TextField(blank=True)  # Exact original string for fingerprint and diagnostics.
    bait1 = models.ForeignKey(
        Bait, null=True, blank=True, on_delete=models.PROTECT,
        related_name="first_bait_catches", verbose_name="Первая наживка",
    )
    bait2 = models.ForeignKey(
        Bait, null=True, blank=True, on_delete=models.PROTECT,
        related_name="second_bait_catches", verbose_name="Вторая наживка",
    )
    weight_g = models.PositiveIntegerField()
    player = models.CharField(max_length=200)
    caught_date = models.DateField(db_index=True)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    fish_icon_url = models.URLField(max_length=600, blank=True)
    bait_icon_url = models.URLField(max_length=600, blank=True)

    class Meta:
        db_table = "records_catches"
        ordering = ("-caught_date", "-weight_g")
        indexes = [
            models.Index(fields=("waterbody", "caught_date"), name="rec_wb_date_idx"),
            models.Index(fields=("fish", "caught_date"), name="rec_fish_date_idx"),
        ]
        verbose_name = "Улов"
        verbose_name_plural = "Уловы рекордов"

    def __str__(self):
        return f"{self.fish_name}, {self.weight_g} г — {self.caught_date}"


class WeeklyCatchRegion(models.Model):
    """One row per catch and weekly region, NOT one row per polling run."""

    catch = models.ForeignKey(Catch, on_delete=models.CASCADE, related_name="weekly_regions")
    region = models.CharField(max_length=2)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()

    class Meta:
        db_table = "records_weekly_regions"
        constraints = [models.UniqueConstraint(fields=("catch", "region"), name="rec_unique_catch_region")]
        indexes = [models.Index(fields=("region", "catch"), name="rec_region_catch_idx")]
        verbose_name = "Недельный регион улова"
        verbose_name_plural = "Недельные регионы уловов"

    def __str__(self):
        return f"{self.region}: {self.catch_id}"

from django.db import models


class Fish(models.Model):
    class Rarity(models.IntegerChoices):
        COMMON = 1, "Обычная"
        RARE = 2, "Редкая"
        VERY_RARE = 3, "Очень редкая"

    name = models.CharField("Название", max_length=150, unique=True)
    trophy_weight = models.PositiveIntegerField("Трофейный вес, г")
    super_trophy_weight = models.PositiveIntegerField(
        "Супертрофейный вес, г", null=True, blank=True
    )
    rarity = models.PositiveSmallIntegerField(
        "Редкость", choices=Rarity.choices, default=Rarity.COMMON
    )
    description = models.TextField("Описание", blank=True)
    image = models.ImageField("Иконка", upload_to="fish/icons/", blank=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Рыба"
        verbose_name_plural = "Рыбы"
        ordering = ("name",)

    def __str__(self):
        return self.name


class WaterbodyFish(models.Model):
    waterbody = models.ForeignKey(
        "waterbodies.Waterbody",
        on_delete=models.CASCADE,
        related_name="waterbody_fish",
        verbose_name="Водоём",
    )
    fish = models.ForeignKey(
        Fish,
        on_delete=models.CASCADE,
        related_name="waterbody_fish",
        verbose_name="Рыба",
    )

    class Meta:
        verbose_name = "Рыба водоёма"
        verbose_name_plural = "Рыбы водоёмов"
        constraints = [
            models.UniqueConstraint(
                fields=("waterbody", "fish"),
                name="unique_waterbody_fish",
            )
        ]

    def __str__(self):
        return f"{self.waterbody} — {self.fish}"

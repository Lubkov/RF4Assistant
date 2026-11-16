from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def fishing_spot_screenshot_path(instance, filename):
    """Use a unique WebP filename; actual image conversion belongs to upload service."""
    return f"fishing_spots/screenshots/{uuid4().hex}.webp"


class FishingSpot(models.Model):
    waterbody = models.ForeignKey(
        "waterbodies.Waterbody", on_delete=models.PROTECT,
        related_name="fishing_spots", verbose_name="Водоём",
    )
    x = models.FloatField("Координата X")
    y = models.FloatField("Координата Y")
    clip = models.PositiveIntegerField(
        "Клипса", null=True, blank=True, validators=[MinValueValidator(1)],
    )
    depth_cm = models.PositiveIntegerField(
        "Глубина, см", null=True, blank=True, validators=[MinValueValidator(1)],
    )
    retrieve_speed = models.PositiveSmallIntegerField(
        "Скорость проводки", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
    )
    is_mixed_fish = models.BooleanField("Разнорыбица", default=False)
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, db_index=True)
    fish = models.ManyToManyField(
        "fish.Fish", through="FishingSpotFish", related_name="fishing_spots",
        verbose_name="Виды рыб", blank=True,
    )

    class Meta:
        verbose_name = "Место ловли"
        verbose_name_plural = "Места ловли"
        ordering = ("-created_at", "-pk")

    def __str__(self):
        return f"{self.waterbody} — {self.x:g}:{self.y:g}"

    def clean(self):
        super().clean()
        if not self.waterbody_id:
            return
        try:
            game_map = self.waterbody.game_map
        except self.waterbody.__class__.game_map.RelatedObjectDoesNotExist:
            raise ValidationError({"waterbody": "У водоёма отсутствует игровая карта."})
        if not game_map.has_game_coordinates:
            raise ValidationError({"waterbody": "Границы координат карты не настроены."})
        errors = {}
        if self.x is not None and not (game_map.game_x_min <= self.x <= game_map.game_x_max):
            errors["x"] = "Координата X вне границ карты."
        if self.y is not None and not (game_map.game_y_min <= self.y <= game_map.game_y_max):
            errors["y"] = "Координата Y вне границ карты."
        if errors:
            raise ValidationError(errors)


class FishingSpotCategory(models.Model):
    class Category(models.TextChoices):
        FARM = "farm", "Фарм"
        TROPHY = "trophy", "Трофей"
        QUALIFICATION = "qualification", "Квалификация"
        TASK = "task", "Задание"

    fishing_spot = models.ForeignKey(
        FishingSpot, on_delete=models.CASCADE, related_name="categories",
        verbose_name="Место ловли",
    )
    category = models.CharField("Категория", max_length=20, choices=Category.choices)

    class Meta:
        verbose_name = "Категория места ловли"
        verbose_name_plural = "Категории мест ловли"
        constraints = [
            models.UniqueConstraint(
                fields=("fishing_spot", "category"),
                name="unique_fishing_spot_category",
            ),
        ]

    def __str__(self):
        return self.get_category_display()


class FishingSpotFish(models.Model):
    fishing_spot = models.ForeignKey(
        FishingSpot, on_delete=models.CASCADE, related_name="spot_fish",
        verbose_name="Место ловли",
    )
    fish = models.ForeignKey(
        "fish.Fish", on_delete=models.PROTECT,
        related_name="fishing_spot_links", verbose_name="Рыба",
    )

    class Meta:
        verbose_name = "Рыба места ловли"
        verbose_name_plural = "Рыбы мест ловли"
        constraints = [
            models.UniqueConstraint(
                fields=("fishing_spot", "fish"),
                name="unique_fishing_spot_fish",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.fishing_spot_id or not self.fish_id:
            return
        if self.fishing_spot.is_mixed_fish:
            raise ValidationError("Для 'Разнорыбицы' нельзя выбирать конкретные виды рыб.")
        from fish.models import WaterbodyFish
        if not WaterbodyFish.objects.filter(
            waterbody_id=self.fishing_spot.waterbody_id, fish_id=self.fish_id,
        ).exists():
            raise ValidationError({"fish": "Рыба не привязана к выбранному водоёму."})

    def __str__(self):
        return str(self.fish)


class FishingSpotScreenshot(models.Model):
    fishing_spot = models.ForeignKey(
        FishingSpot, on_delete=models.CASCADE, related_name="screenshots",
        verbose_name="Место ловли",
    )
    image = models.ImageField("Скриншот", upload_to=fishing_spot_screenshot_path)
    position = models.PositiveSmallIntegerField(
        "Позиция", validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "Скриншот места ловли"
        verbose_name_plural = "Скриншоты мест ловли"
        ordering = ("position", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("fishing_spot", "position"),
                name="unique_fishing_spot_screenshot_position",
            ),
        ]

    def __str__(self):
        return f"Скриншот №{self.position}"

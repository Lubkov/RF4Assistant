from django.db import models


class Waterbody(models.Model):
    name = models.CharField("Название", max_length=150)
    level = models.PositiveSmallIntegerField("Уровень доступа")
    slug = models.SlugField("URL-идентификатор", max_length=150, unique=True)
    description = models.TextField("Описание", blank=True)
    image = models.ImageField(
        "Изображение", upload_to="waterbodies/", blank=True
    )
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Водоём"
        verbose_name_plural = "Водоёмы"
        ordering = ("level", "id")

    def __str__(self):
        return self.name


class WaterbodyMap(models.Model):
    """Game map image, independent from the waterbody's landscape card image."""

    waterbody = models.OneToOneField(
        Waterbody, on_delete=models.CASCADE, related_name="game_map",
        verbose_name="Водоём",
    )
    image = models.ImageField(
        "Игровая карта", upload_to="waterbodies/maps/",
    )
    source_url = models.URLField("Источник изображения", blank=True)

    class Meta:
        verbose_name = "Карта водоёма"
        verbose_name_plural = "Карты водоёмов"

    def __str__(self):
        return f"Карта: {self.waterbody.name}"

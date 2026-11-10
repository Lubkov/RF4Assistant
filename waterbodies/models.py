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

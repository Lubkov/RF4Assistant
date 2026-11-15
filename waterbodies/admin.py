from django.contrib import admin
from django import forms
from django.utils.html import format_html

from fish.models import WaterbodyFish
from .models import Waterbody, WaterbodyMap


class WaterbodyFishInline(admin.TabularInline):
    """Edit a waterbody's fish without changing the fish catalogue."""

    model = WaterbodyFish
    autocomplete_fields = ("fish",)
    extra = 0
    verbose_name = "Рыба водоёма"
    verbose_name_plural = "Рыбы водоёма"


class WaterbodyMapForm(forms.ModelForm):
    class Meta:
        model = WaterbodyMap
        fields = "__all__"

    def clean(self):
        data = super().clean()
        names = ("game_x_min", "game_x_max", "game_y_min", "game_y_max")
        values = [data.get(name) for name in names]
        if any(value is not None for value in values) and not all(value is not None for value in values):
            raise forms.ValidationError("Укажите все четыре границы игровых координат.")
        if all(value is not None for value in values):
            if data["game_x_min"] >= data["game_x_max"] or data["game_y_min"] >= data["game_y_max"]:
                raise forms.ValidationError("Минимальная координата должна быть меньше максимальной.")
        return data


MAP_CALIBRATION_FIELDS = (
    "game_x_min", "game_x_max", "game_y_min", "game_y_max",
)


class WaterbodyMapInline(admin.StackedInline):
    form = WaterbodyMapForm
    model = WaterbodyMap
    extra = 1
    max_num = 1
    fields = ("image", "source_url", MAP_CALIBRATION_FIELDS)
    verbose_name = "Игровая карта"
    verbose_name_plural = "Игровая карта"


@admin.register(WaterbodyMap)
class WaterbodyMapAdmin(admin.ModelAdmin):
    form = WaterbodyMapForm
    list_display = ("waterbody", "source_url")
    search_fields = ("waterbody__name",)
    autocomplete_fields = ("waterbody",)
    readonly_fields = ("map_preview",)
    fields = ("waterbody", "image", "source_url", MAP_CALIBRATION_FIELDS, "map_preview")

    @admin.display(description="Предпросмотр карты")
    def map_preview(self, obj):
        if not obj or not obj.image:
            return "Карта не загружена"
        return format_html(
            '<img src="{}" alt="{}" style="max-width:360px;width:100%;height:auto;" />',
            obj.image.url, obj.waterbody.name,
        )


@admin.register(Waterbody)
class WaterbodyAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "is_active", "sort_order", "has_image")
    list_display_links = ("name",)
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active", "level")
    search_fields = ("name", "slug")
    ordering = ("level", "id")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("image_preview",)
    fields = (
        "name", "level", "slug", "description", "image", "image_preview",
        "sort_order", "is_active",
    )
    inlines = (WaterbodyMapInline, WaterbodyFishInline)

    @admin.display(boolean=True, description="Изображение")
    def has_image(self, obj):
        return bool(obj.image)

    @admin.display(description="Предпросмотр")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "Изображение не загружено"
        return format_html(
            '<img src="{}" alt="{}" style="max-width:320px;max-height:180px;object-fit:contain;" />',
            obj.image.url,
            obj.name,
        )

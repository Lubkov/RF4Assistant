from django.contrib import admin
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


class WaterbodyMapInline(admin.StackedInline):
    model = WaterbodyMap
    extra = 1
    max_num = 1
    fields = ("image", "source_url")
    verbose_name = "Игровая карта"
    verbose_name_plural = "Игровая карта"


@admin.register(WaterbodyMap)
class WaterbodyMapAdmin(admin.ModelAdmin):
    list_display = ("waterbody", "source_url")
    search_fields = ("waterbody__name",)
    autocomplete_fields = ("waterbody",)
    readonly_fields = ("map_preview",)
    fields = ("waterbody", "image", "source_url", "map_preview")

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

"""Django Admin for shared fishing spots."""

import re

from django import forms
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html

from fish.models import WaterbodyFish
from .models import (
    FishingSpot,
    FishingSpotCategory,
    FishingSpotFish,
    FishingSpotScreenshot,
)
from .views import convert_image


class CountLimitedInlineFormSet(BaseInlineFormSet):
    minimum_items = 0
    maximum_items = None
    item_label = "записей"

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        selected = [
            form for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]
        if len(selected) < self.minimum_items or (
            self.maximum_items is not None and len(selected) > self.maximum_items
        ):
            raise forms.ValidationError(
                f"Допустимое количество {self.item_label}: "
                f"от {self.minimum_items} до {self.maximum_items}."
            )
        self.validate_selected(selected)

    def validate_selected(self, selected):
        pass


class CategoryInlineFormSet(CountLimitedInlineFormSet):
    minimum_items = 1
    maximum_items = 2
    item_label = "категорий"


class FishInlineFormSet(CountLimitedInlineFormSet):
    maximum_items = 5
    item_label = "видов рыб"

    def validate_selected(self, selected):
        if self.instance.is_mixed_fish:
            if selected:
                raise forms.ValidationError(
                    "Если выбрана «Разнорыбица», конкретные виды рыб указывать нельзя."
                )
            return
        if not 1 <= len(selected) <= 5:
            raise forms.ValidationError("Выберите от 1 до 5 видов рыб или «Разнорыбицу».")
        if not self.instance.waterbody_id:
            return
        fish_ids = {form.cleaned_data["fish"].pk for form in selected}
        valid_ids = set(WaterbodyFish.objects.filter(
            waterbody_id=self.instance.waterbody_id, fish_id__in=fish_ids,
        ).values_list("fish_id", flat=True))
        if fish_ids != valid_ids:
            raise forms.ValidationError("Выбранная рыба должна обитать в указанном водоёме.")


class ScreenshotInlineFormSet(CountLimitedInlineFormSet):
    minimum_items = 2
    maximum_items = 10
    item_label = "скриншотов"

    def validate_selected(self, selected):
        positions = [form.cleaned_data.get("position") for form in selected]
        if None not in positions and len(positions) != len(set(positions)):
            raise forms.ValidationError("Порядковые номера скриншотов должны быть уникальными.")


class CategoryInline(admin.TabularInline):
    model = FishingSpotCategory
    formset = CategoryInlineFormSet
    extra = 1
    max_num = 2
    fields = ("category",)
    verbose_name = "Категория"
    verbose_name_plural = "Категории"


class FishInline(admin.TabularInline):
    model = FishingSpotFish
    formset = FishInlineFormSet
    autocomplete_fields = ("fish",)
    extra = 1
    max_num = 5
    verbose_name = "Вид рыбы"
    verbose_name_plural = "Виды рыб (не заполнять для «Разнорыбицы»)"


class ScreenshotAdminForm(forms.ModelForm):
    class Meta:
        model = FishingSpotScreenshot
        fields = "__all__"

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "content_type"):
            try:
                return convert_image(image)
            except ValueError as exc:
                raise forms.ValidationError(str(exc)) from exc
        return image


class ScreenshotInline(admin.TabularInline):
    form = ScreenshotAdminForm
    model = FishingSpotScreenshot
    formset = ScreenshotInlineFormSet
    extra = 1
    max_num = 10
    readonly_fields = ("image_preview",)
    fields = ("position", "image", "image_preview")
    verbose_name = "Скриншот"
    verbose_name_plural = "Скриншоты (№ 1 — обложка)"

    @admin.display(description="Превью")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "—"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">'
            '<img src="{}" alt="Скриншот №{}" '
            'style="max-width:180px;max-height:110px;object-fit:contain;border-radius:5px" />'
            '</a>', obj.image.url, obj.image.url, obj.position,
        )


class CategoryFilter(admin.SimpleListFilter):
    title = "категория"
    parameter_name = "spot_category"

    def lookups(self, request, model_admin):
        return FishingSpotCategory.Category.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(categories__category=self.value())
        return queryset


@admin.register(FishingSpot)
class FishingSpotAdmin(admin.ModelAdmin):
    list_display = (
        "id", "waterbody", "coordinates", "category_names",
        "fish_names", "created_at",
    )
    list_display_links = ("id", "coordinates")
    list_filter = ("waterbody", CategoryFilter, ("created_at", admin.DateFieldListFilter))
    search_fields = ("comment", "waterbody__name")
    search_help_text = "Поиск по водоёму, комментарию или координатам в формате X:Y (например, 33:44)."
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_select_related = ("waterbody",)
    list_per_page = 50
    readonly_fields = ("created_at",)
    fields = (
        "waterbody", "x", "y", "clip", "depth_cm", "retrieve_speed",
        "is_mixed_fish", "comment", "created_at",
    )
    inlines = (CategoryInline, FishInline, ScreenshotInline)
    save_on_top = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "categories", "spot_fish__fish",
        )

    @admin.display(description="Координаты", ordering="x")
    def coordinates(self, obj):
        return f"{obj.x:g}:{obj.y:g}"

    @admin.display(description="Категории")
    def category_names(self, obj):
        return ", ".join(item.get_category_display() for item in obj.categories.all()) or "—"

    @admin.display(description="Виды рыб")
    def fish_names(self, obj):
        if obj.is_mixed_fish:
            return "Разнорыбица"
        return ", ".join(link.fish.name for link in obj.spot_fish.all()) or "—"

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term,
        )
        match = re.fullmatch(
            r"\s*([+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*:\s*"
            r"([+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*",
            search_term,
        )
        if match:
            x, y = (float(part.replace(",", ".")) for part in match.groups())
            queryset = queryset | self.get_queryset(request).filter(x=x, y=y)
        return queryset, may_have_duplicates


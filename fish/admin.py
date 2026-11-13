from django.contrib import admin

from .models import Fish


@admin.register(Fish)
class FishAdmin(admin.ModelAdmin):
    list_display = (
        "name", "image", "rarity", "trophy_weight", "super_trophy_weight", "is_active",
    )
    list_display_links = ("name",)
    list_filter = ("rarity", "is_active")
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50
    fields = (
        "name", "rarity", "trophy_weight", "super_trophy_weight",
        "description", "image", "is_active",
    )

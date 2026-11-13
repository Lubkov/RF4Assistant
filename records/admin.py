from django.contrib import admin
from .models import Bait, Catch, Collection, WeeklyCatchRegion


@admin.register(Bait)
class BaitAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "image")
    search_fields = ("name",)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("id", "region", "record_type", "collected_at", "record_count", "new_record_count")
    list_filter = ("region", "record_type")
    ordering = ("-collected_at",)


@admin.register(Catch)
class CatchAdmin(admin.ModelAdmin):
    list_display = ("id", "fish_name", "waterbody_name", "weight_g", "bait", "bait1", "bait2", "caught_date", "fish", "waterbody")
    list_filter = ("caught_date",)
    search_fields = ("fish_name", "waterbody_name", "player", "bait")
    raw_id_fields = ("fish", "waterbody", "bait1", "bait2", "collection")
    readonly_fields = ("fingerprint", "first_seen_at", "last_seen_at")


@admin.register(WeeklyCatchRegion)
class WeeklyCatchRegionAdmin(admin.ModelAdmin):
    list_display = ("catch_id", "region", "first_seen_at", "last_seen_at")
    list_filter = ("region",)
    raw_id_fields = ("catch",)

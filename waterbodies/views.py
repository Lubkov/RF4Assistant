from django.shortcuts import get_object_or_404, render

from fish.models import Fish

from .models import Waterbody, WaterbodyMap


def waterbody_detail(request, slug):
    waterbodies = Waterbody.objects.filter(is_active=True).order_by("level", "id")
    waterbody = get_object_or_404(Waterbody, slug=slug, is_active=True)
    game_map = WaterbodyMap.objects.filter(waterbody=waterbody).first()
    fishes = Fish.objects.filter(
        waterbody_fish__waterbody=waterbody, is_active=True
    ).order_by("name", "id")
    return render(
        request, "waterbodies/detail.html",
        {"waterbody": waterbody, "game_map": game_map, "fishes": fishes, "waterbodies": waterbodies},
    )

from django.shortcuts import get_object_or_404, render

from .models import Waterbody, WaterbodyMap


def waterbody_detail(request, slug):
    waterbodies = Waterbody.objects.filter(is_active=True).order_by("level", "id")
    waterbody = get_object_or_404(Waterbody, slug=slug, is_active=True)
    game_map = WaterbodyMap.objects.filter(waterbody=waterbody).first()
    return render(
        request, "waterbodies/detail.html",
        {"waterbody": waterbody, "game_map": game_map, "waterbodies": waterbodies},
    )

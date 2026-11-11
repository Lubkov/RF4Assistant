from django.shortcuts import render

from waterbodies.models import Waterbody

from .models import Fish


def fish_list(request):
    # Only active entries appear in the public reference list.
    fishes = Fish.objects.filter(is_active=True).order_by("name", "id")
    waterbodies = Waterbody.objects.filter(is_active=True).order_by("level", "id")
    return render(request, "fish/list.html", {"fishes": fishes, "waterbodies": waterbodies})

from django.shortcuts import render

from waterbodies.models import Waterbody


def home(request):
    waterbodies = Waterbody.objects.filter(is_active=True).order_by("level", "id")
    return render(request, "core/home.html", {"waterbodies": waterbodies})

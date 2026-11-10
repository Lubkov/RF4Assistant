from django.shortcuts import render


def home(request):
    # Waterbody cards will be populated in the models/data-migration phase.
    return render(request, "core/home.html")

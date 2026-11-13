from datetime import timedelta

from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone

from fish.models import Fish
from waterbodies.models import Waterbody
from .analytics import SORT_OPTIONS, report
from .sources import REGION_NAMES


def weekly_report(request):
    today = timezone.localdate()
    start = request.GET.get("date_from", (today - timedelta(days=1)).isoformat())
    end = request.GET.get("date_to", today.isoformat())
    region = request.GET.get("region", "ALL").upper()
    sort = request.GET.get("sort", "count")
    try:
        wb = int(request.GET["waterbody_id"]) if request.GET.get("waterbody_id") else None
        fish = int(request.GET["fish_id"]) if request.GET.get("fish_id") else None
        data = report(
            date_from=start, date_to=end,
            waterbody_id=wb, fish_id=fish, region=region, sort=sort,
        )
    except (ValueError, OverflowError) as exc:
        return HttpResponseBadRequest(f"Некорректные параметры отчёта: {exc}")
    return render(request, "records/weekly.html", {
        "data": data,
        "waterbodies": Waterbody.objects.order_by("name"),
        "fishes": Fish.objects.order_by("name"),
        "selected_waterbody": wb,
        "selected_fish": fish,
        "regions": REGION_NAMES,
        "selected_region": region,
        "sort_options": SORT_OPTIONS,
    })

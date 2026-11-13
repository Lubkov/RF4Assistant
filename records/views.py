from datetime import timedelta

from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone

from fish.models import Fish
from waterbodies.models import Waterbody
from .analytics import SORT_OPTIONS, report, bait_report
from .sources import REGION_NAMES


def weekly_report(request):
    today = timezone.localdate()
    try:
        days = int(request.GET.get("days", "1"))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Некорректный период")
    if days not in (1, 2, 3, 7):
        return HttpResponseBadRequest("Недопустимый период")
    start = (today - timedelta(days=days - 1)).isoformat()
    end = today.isoformat()
    # Show all regions by default; individual region selection remains available.
    region = request.GET.get("region", "ALL").upper() or "ALL"
    if region != "ALL" and region not in REGION_NAMES:
        return HttpResponseBadRequest("Некорректный регион")
    view = request.GET.get("view", "fish")
    if view not in ("fish", "bait"):
        return HttpResponseBadRequest("Некорректный вид отчёта")
    sort = request.GET.get("sort", "count")
    if view == "bait" and sort == "fish":
        sort = "name"
    if view == "fish" and sort == "name":
        sort = "fish"
    waterbodies = Waterbody.objects.order_by("sort_order", "name", "id")
    first_waterbody = waterbodies.values_list("pk", flat=True).first()
    try:
        if "waterbody_id" in request.GET:
            wb = int(request.GET["waterbody_id"]) if request.GET.get("waterbody_id") else first_waterbody
        else:
            wb = first_waterbody
        fish = int(request.GET["fish_id"]) if request.GET.get("fish_id") else None
        data = (bait_report if view == "bait" else report)(
            date_from=start, date_to=end,
            waterbody_id=wb, fish_id=fish, region=region, sort=sort,
        )
    except (ValueError, OverflowError) as exc:
        return HttpResponseBadRequest(f"Некорректные параметры отчёта: {exc}")
    query = request.GET.copy()
    tabs = {}
    for tab in ("fish", "bait"):
        query["view"] = tab
        if tab == "bait" and query.get("sort") == "fish":
            query["sort"] = "name"
        elif tab == "fish" and query.get("sort") == "name":
            query["sort"] = "fish"
        tabs[tab] = "?" + query.urlencode()
    return render(request, "records/weekly.html", {
        "data": data,
        "waterbodies": waterbodies,
        "selected_days": days,
        "fishes": Fish.objects.order_by("name"),
        "selected_waterbody": wb,
        "selected_fish": fish,
        "regions": REGION_NAMES,
        "selected_region": region,
        "sort_options": (
            (("count", "Количество рекордов"), ("weight", "Максимальный вес"), ("name", "Название наживки"))
            if view == "bait" else SORT_OPTIONS
        ),
        "selected_view": view,
        "view_urls": tabs,
    })

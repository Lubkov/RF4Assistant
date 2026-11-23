from datetime import timedelta
from urllib.parse import urlencode

from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from fish.models import Fish
from waterbodies.models import Waterbody
from .analytics import SORT_OPTIONS, report, bait_report
from .sources import REGION_NAMES


def weekly_report(request, fish_details=False):
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
    if fish_details:
        try:
            group = {}
            for field in ("waterbody", "fish"):
                group_id = request.GET.get(f"{field}_id")
                if group_id is not None:
                    group[f"{field}_id"] = int(group_id)
                elif f"{field}_name" in request.GET:
                    group[f"{field}_name"] = request.GET[f"{field}_name"]
                else:
                    raise ValueError("Missing record group")
            rows = report(date_from=start, date_to=end, region=region, **group)["rows"]
        except (ValueError, OverflowError):
            return HttpResponseBadRequest("Некорректная группа рекордов")
        if not rows:
            raise Http404
        return render(request, "records/_fish_details.html", {"row": rows[0]})

    view = request.GET.get("view", "fish")
    if view not in ("fish", "bait"):
        return HttpResponseBadRequest("Некорректный вид отчёта")
    sort = request.GET.get("sort", "count")
    if view == "bait":
        sort = "count"
    elif sort == "name":
        sort = "fish"
    waterbodies = Waterbody.objects.order_by("sort_order", "name", "id")
    first_waterbody = waterbodies.values_list("pk", flat=True).first()
    try:
        if "waterbody_id" in request.GET:
            wb = int(request.GET["waterbody_id"]) if request.GET.get("waterbody_id") else first_waterbody
        else:
            wb = first_waterbody
        fish = int(request.GET["fish_id"]) if request.GET.get("fish_id") else None
        # Filter species in one direction only: waterbody -> fish.
        # The WaterbodyFish catalog is populated from record imports and admin.
        fishes = Fish.objects.filter(
            waterbody_fish__waterbody_id=wb
        ).order_by("name")
        if fish is not None and not fishes.filter(pk=fish).exists():
            fish = None
        report_filters = dict(
            date_from=start, date_to=end,
            waterbody_id=wb, fish_id=fish, region=region, sort=sort,
        )
        if view == "fish":
            data = report(**report_filters, bait_limit=3)
        else:
            data = bait_report(**report_filters)
            for row in data["rows"]:
                row["fish_preview"] = row["fish_details"][:3]
                row["remaining_fish_count"] = len(row["fish_details"]) - len(row["fish_preview"])
    except (ValueError, OverflowError) as exc:
        return HttpResponseBadRequest(f"Некорректные параметры отчёта: {exc}")
    if view == "fish":
        details_url = reverse("records:fish_details")
        for row in data["rows"]:
            row["remaining_bait_count"] = row["bait_count"] - len(row["bait_details"])
            params = {"days": days, "region": region}
            for field in ("waterbody", "fish"):
                if row[f"{field}_id"] is not None:
                    params[f"{field}_id"] = row[f"{field}_id"]
                else:
                    params[f"{field}_name"] = row[field]
            row["details_url"] = f"{details_url}?{urlencode(params)}"
    query = request.GET.copy()
    # Do not carry an invalid species over when switching between report tabs.
    if fish is None:
        query.pop("fish_id", None)
    tabs = {}
    for tab in ("fish", "bait"):
        query["view"] = tab
        if tab == "bait":
            query.pop("sort", None)
        elif tab == "fish" and query.get("sort") == "name":
            query["sort"] = "fish"
        tabs[tab] = "?" + query.urlencode()
    return render(request, "records/weekly.html", {
        "data": data,
        "waterbodies": waterbodies,
        "selected_days": days,
        "fishes": fishes,
        "selected_waterbody": wb,
        "selected_fish": fish,
        "regions": REGION_NAMES,
        "selected_region": region,
        "sort_options": SORT_OPTIONS,
        "selected_view": view,
        "view_urls": tabs,
    })

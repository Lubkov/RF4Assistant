"""Summary of distinct weekly catches, grouped by waterbody, fish and bait combination."""
from collections import Counter
from datetime import date

from django.db.models import Exists, OuterRef

from fish.models import Fish
from .models import Bait, Catch, WeeklyCatchRegion
from .sources import REGION_NAMES


SORT_OPTIONS = (
    ("count", "Количество рекордов"),
    ("weight", "Максимальный вес"),
    ("fish", "Название рыбы"),
)


def format_weight(weight_g):
    """Human-readable weight with no loss of gram precision."""
    return f"{weight_g / 1000:,.3f}".replace(",", " ") + " кг" if weight_g >= 1000 else f"{weight_g} г"


def report(*, date_from, date_to, waterbody_id=None, fish_id=None, region="ALL", sort="count"):
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)
    if isinstance(date_to, str):
        date_to = date.fromisoformat(date_to)
    if date_from > date_to:
        raise ValueError("date_from must be <= date_to")
    region = region.upper()
    if region != "ALL" and region not in REGION_NAMES:
        raise ValueError("Unknown region")
    if sort not in dict(SORT_OPTIONS):
        raise ValueError("Unknown sort order")

    weekly = WeeklyCatchRegion.objects.filter(catch_id=OuterRef("pk"))
    if region != "ALL":
        weekly = weekly.filter(region=region)
    qs = Catch.objects.annotate(in_weekly=Exists(weekly)).filter(
        in_weekly=True,
        caught_date__range=(date_from, date_to),
    )
    if waterbody_id is not None:
        qs = qs.filter(waterbody_id=waterbody_id)
    if fish_id is not None:
        qs = qs.filter(fish_id=fish_id)

    groups = {}
    # The query reads only required fields and avoids a DB request per record.
    values = (
        "waterbody_id", "waterbody_name", "fish_id", "fish_name", "weight_g",
        "bait", "bait1_id", "bait2_id",
    )
    for catch in qs.values(*values).iterator():
        key = (
            ("id", catch["waterbody_id"]) if catch["waterbody_id"] is not None else ("name", catch["waterbody_name"]),
            ("id", catch["fish_id"]) if catch["fish_id"] is not None else ("name", catch["fish_name"]),
        )
        row = groups.setdefault(key, {
            "waterbody_id": catch["waterbody_id"],
            "waterbody": catch["waterbody_name"],
            "fish_id": catch["fish_id"],
            "fish": catch["fish_name"],
            "max_weight_g": 0,
            "record_count": 0,
            "baits": Counter(),
            "bait_icons": {},
        })
        row["record_count"] += 1
        row["max_weight_g"] = max(row["max_weight_g"], catch["weight_g"])
        components = [part.strip() for part in (catch["bait"] or "").split(";") if part.strip()]
        bait_label = " и ".join(components) if components else "(не указана)"
        row["baits"][bait_label] += 1
        # Only the first bait has an icon on the source website, but both can
        # have local icons once they have appeared in the first position.
        ids = (catch["bait1_id"], catch["bait2_id"])
        if bait_label not in row["bait_icons"] or not any(row["bait_icons"][bait_label]):
            row["bait_icons"][bait_label] = ids

    fish_ids = {g["fish_id"] for g in groups.values() if g["fish_id"] is not None}
    fish_images = {
        pk: image for pk, image in Fish.objects.filter(pk__in=fish_ids).values_list("pk", "image")
        if image
    }
    bait_ids = {
        bid for g in groups.values() for pair in g["bait_icons"].values()
        for bid in pair if bid is not None
    }
    bait_images = {
        pk: image for pk, image in Bait.objects.filter(pk__in=bait_ids).values_list("pk", "image")
        if image
    }
    # ImageField stores paths relative to MEDIA_URL; do not construct guessed URLs.
    from django.core.files.storage import default_storage

    def image_url(path):
        if not path:
            return None
        return default_storage.url(path)

    waterbodies = {}
    for item in groups.values():
        item["fish_image_url"] = image_url(fish_images.get(item["fish_id"]))
        item["weight_display"] = format_weight(item["max_weight_g"])
        item["bait_details"] = [
            {
                "bait": name,
                "count": count,
                "images": [image_url(bait_images.get(bid)) for bid in item["bait_icons"].get(name, ()) if bid],
            }
            for name, count in sorted(item["baits"].items(), key=lambda entry: (-entry[1], entry[0]))
        ]
        item["baits"] = [{"bait": b["bait"], "count": b["count"]} for b in item["bait_details"]]
        del item["bait_icons"]
        wb_key = ("id", item["waterbody_id"]) if item["waterbody_id"] is not None else ("name", item["waterbody"])
        wb = waterbodies.setdefault(wb_key, {
            "id": item["waterbody_id"], "name": item["waterbody"],
            "record_count": 0, "fish_count": 0, "rows": [],
        })
        wb["record_count"] += item["record_count"]
        wb["fish_count"] += 1
        wb["rows"].append(item)

    def row_sort(item):
        if sort == "weight":
            return (-item["max_weight_g"], -item["record_count"], item["fish"].casefold())
        if sort == "fish":
            return (item["fish"].casefold(), -item["record_count"])
        return (-item["record_count"], -item["max_weight_g"], item["fish"].casefold())

    result_groups = list(waterbodies.values())
    for wb in result_groups:
        wb["rows"].sort(key=row_sort)
    result_groups.sort(key=lambda wb: (-wb["record_count"], wb["name"].casefold()))
    for index, wb in enumerate(result_groups):
        wb["expanded"] = index == 0 or waterbody_id is not None

    # Keep the flat representation for callers that already use report()['rows'].
    rows = [row for wb in result_groups for row in wb["rows"]]
    return {
        "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
        "region": region, "sort": sort,
        "total_unique_catches": sum(wb["record_count"] for wb in result_groups),
        "total_groups": len(rows),
        "total_waterbodies": len(result_groups),
        "waterbody_groups": result_groups,
        "rows": rows,
    }


# Alternative presentation of the very same weekly catches: waterbody -> bait
# combination -> fish species.  One catch is counted in exactly one combination.
def bait_report(*, date_from, date_to, waterbody_id=None, fish_id=None, region="ALL", sort="count"):
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)
    if isinstance(date_to, str):
        date_to = date.fromisoformat(date_to)
    if date_from > date_to:
        raise ValueError("date_from must be <= date_to")
    region = region.upper()
    if region != "ALL" and region not in REGION_NAMES:
        raise ValueError("Unknown region")
    if sort not in ("count", "weight", "name"):
        raise ValueError("Unknown sort order")

    weekly = WeeklyCatchRegion.objects.filter(catch_id=OuterRef("pk"))
    if region != "ALL":
        weekly = weekly.filter(region=region)
    qs = Catch.objects.annotate(in_weekly=Exists(weekly)).filter(
        in_weekly=True, caught_date__range=(date_from, date_to)
    )
    if waterbody_id is not None:
        qs = qs.filter(waterbody_id=waterbody_id)
    if fish_id is not None:
        qs = qs.filter(fish_id=fish_id)

    groups = {}
    fields = (
        "waterbody_id", "waterbody_name", "fish_id", "fish_name",
        "weight_g", "bait", "bait1_id", "bait2_id",
    )
    for catch in qs.values(*fields).iterator():
        components = [v.strip() for v in (catch["bait"] or "").split(";") if v.strip()]
        bait_name = " и ".join(components) if components else "(не указана)"
        wb_key = ("id", catch["waterbody_id"]) if catch["waterbody_id"] is not None else ("name", catch["waterbody_name"])
        group_key = (wb_key, bait_name)
        row = groups.setdefault(group_key, {
            "waterbody_id": catch["waterbody_id"], "waterbody": catch["waterbody_name"],
            "bait": bait_name, "bait_ids": (None, None),
            "max_weight_g": 0, "record_count": 0, "fishes": {},
        })
        row["record_count"] += 1
        row["max_weight_g"] = max(row["max_weight_g"], catch["weight_g"])
        if not any(row["bait_ids"]):
            row["bait_ids"] = (catch["bait1_id"], catch["bait2_id"])
        fish_key = ("id", catch["fish_id"]) if catch["fish_id"] is not None else ("name", catch["fish_name"])
        fish = row["fishes"].setdefault(fish_key, {
            "fish_id": catch["fish_id"], "fish": catch["fish_name"], "count": 0,
        })
        fish["count"] += 1

    fish_ids = {fish["fish_id"] for g in groups.values() for fish in g["fishes"].values() if fish["fish_id"] is not None}
    bait_ids = {bid for g in groups.values() for bid in g["bait_ids"] if bid is not None}
    fish_images = dict(Fish.objects.filter(pk__in=fish_ids).exclude(image="").values_list("pk", "image"))
    bait_images = dict(Bait.objects.filter(pk__in=bait_ids).exclude(image="").values_list("pk", "image"))
    from django.core.files.storage import default_storage

    def image_url(path):
        return default_storage.url(path) if path else None

    waterbodies = {}
    for row in groups.values():
        row["weight_display"] = format_weight(row["max_weight_g"])
        row["bait_images"] = [image_url(bait_images.get(bid)) for bid in row["bait_ids"] if bid and bait_images.get(bid)]
        row["fish_details"] = sorted((
            {**fish, "image_url": image_url(fish_images.get(fish["fish_id"]))}
            for fish in row["fishes"].values()
        ), key=lambda item: (-item["count"], item["fish"].casefold()))
        del row["bait_ids"]
        del row["fishes"]
        wb_key = ("id", row["waterbody_id"]) if row["waterbody_id"] is not None else ("name", row["waterbody"])
        wb = waterbodies.setdefault(wb_key, {
            "id": row["waterbody_id"], "name": row["waterbody"],
            "record_count": 0, "bait_count": 0, "rows": [],
        })
        wb["record_count"] += row["record_count"]
        wb["bait_count"] += 1
        wb["rows"].append(row)

    def row_sort(item):
        if sort == "weight":
            return (-item["max_weight_g"], -item["record_count"], item["bait"].casefold())
        if sort == "name":
            return (item["bait"].casefold(), -item["record_count"])
        return (-item["record_count"], -item["max_weight_g"], item["bait"].casefold())

    result_groups = list(waterbodies.values())
    for wb in result_groups:
        wb["rows"].sort(key=row_sort)
    result_groups.sort(key=lambda wb: (-wb["record_count"], wb["name"].casefold()))
    for index, wb in enumerate(result_groups):
        wb["expanded"] = index == 0 or waterbody_id is not None
    rows = [row for wb in result_groups for row in wb["rows"]]
    return {
        "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
        "region": region, "sort": sort,
        "total_unique_catches": sum(wb["record_count"] for wb in result_groups),
        "total_groups": len(rows), "total_waterbodies": len(result_groups),
        "waterbody_groups": result_groups, "rows": rows,
    }

"""Idempotent, incremental imports of weekly RF4 records."""
import hashlib
import json
from datetime import date

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from fish.models import Fish
from waterbodies.models import Waterbody
from .models import Bait, Catch, Collection, WeeklyCatchRegion
from .bait_utils import split_baits
from .sources import classify_url


def fingerprint(record):
    fields = ("fish", "weight_g", "waterbody", "bait", "player", "caught_date")
    raw = json.dumps([record.get(k) for k in fields], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _name_map(model):
    names = {}
    for pk, name in model.objects.values_list("pk", "name"):
        names.setdefault(name.strip().casefold(), pk)
    return names


def import_weekly(payload, *, collected_at=None):
    source = payload.get("source_url", "")
    kind, region = classify_url(source)
    if kind != "weekly" or not region:
        raise ValueError(f"Not a weekly regional source: {source}")
    records = payload.get("records")
    if not isinstance(records, list) or not records or payload.get("record_count") != len(records) or payload.get("warnings"):
        raise ValueError("Empty/partial parse or inconsistent record_count; import rejected")
    distinct = {}
    collisions = []
    for r in records:
        if any(r.get(k) in (None, "") for k in ("fish", "waterbody", "weight_g", "player", "caught_date", "rank")):
            raise ValueError("Incomplete catch record; import rejected")
        if type(r["weight_g"]) is not int or r["weight_g"] <= 0:
            raise ValueError("Invalid weight")
        date.fromisoformat(r["caught_date"])
        key = fingerprint(r)
        if key in distinct:
            collisions.append({"fish": r["fish"], "weight_g": r["weight_g"], "player": r["player"], "caught_date": r["caught_date"], "first_rank": distinct[key]["rank"], "duplicate_rank": r["rank"]})
        else:
            distinct[key] = r
    # Validate bait combinations before starting a database transaction.
    bait_parts = {key: split_baits(r.get("bait")) for key, r in distinct.items()}
    when = collected_at or timezone.now()
    fish_map = _name_map(Fish)
    wb_map = _name_map(Waterbody)
    with transaction.atomic():
        bait_names = sorted({name for parts in bait_parts.values() for name in parts if name})
        known_baits = dict(Bait.objects.filter(name__in=bait_names).values_list("name", "pk"))
        Bait.objects.bulk_create([Bait(name=name) for name in bait_names if name not in known_baits], ignore_conflicts=True)
        known_baits = dict(Bait.objects.filter(name__in=bait_names).values_list("name", "pk"))
        # SQLite single writer; ensure one scheduled worker runs at a time.
        keys = list(distinct)
        existing = {}
        for n in range(0, len(keys), 400):
            existing.update(Catch.objects.filter(fingerprint__in=keys[n:n+400]).values_list("fingerprint", "pk"))
        unseen = [(key, r) for key, r in distinct.items() if key not in existing]
        collection = None
        if unseen:
            collection = Collection.objects.create(
                source_url=source, region=region, record_type="weekly", collected_at=when,
                fish_group_count=payload.get("fish_group_count", 0), record_count=len(records),
                new_record_count=len(unseen),
            )
            Catch.objects.bulk_create([
                Catch(collection=collection, fingerprint=key,
                      fish_id=fish_map.get(r["fish"].strip().casefold()),
                      waterbody_id=wb_map.get(r["waterbody"].strip().casefold()),
                      fish_name=r["fish"], waterbody_name=r["waterbody"],
                      bait=r.get("bait") or "",
                      bait1_id=known_baits.get(bait_parts[key][0]),
                      bait2_id=known_baits.get(bait_parts[key][1]),
                      weight_g=r["weight_g"], player=r["player"],
                      caught_date=date.fromisoformat(r["caught_date"]),
                      first_seen_at=when, last_seen_at=when,
                      fish_icon_url=r.get("fish_icon_url") or "", bait_icon_url=r.get("bait_icon_url") or "")
                for key, r in unseen
            ])
        # Do not duplicate catches. last_seen updates only, even if collection is absent.
        if existing:
            Catch.objects.filter(pk__in=existing.values(), last_seen_at__lt=when).update(last_seen_at=when)
        # Keep image URLs discovered in later collections even for older catches.
        # In particular, bait2 has no image on the RF4 page, but its icon can be
        # obtained when that bait appears as bait1 in another record.
        icon_updates = []
        old_catches = {c.fingerprint: c for c in Catch.objects.filter(fingerprint__in=keys)}
        for key, r in distinct.items():
            c = old_catches[key]
            changed = False
            if r.get("fish_icon_url") and not c.fish_icon_url:
                c.fish_icon_url = r["fish_icon_url"]
                changed = True
            if r.get("bait_icon_url") and not c.bait_icon_url:
                c.bait_icon_url = r["bait_icon_url"]
                changed = True
            if (c.bait1_id is None and bait_parts[key][0] is not None) or (c.bait2_id is None and bait_parts[key][1] is not None):
                c.bait1_id = known_baits.get(bait_parts[key][0])
                c.bait2_id = known_baits.get(bait_parts[key][1])
                changed = True
            if changed:
                icon_updates.append(c)
        if icon_updates:
            Catch.objects.bulk_update(icon_updates, ["fish_icon_url", "bait_icon_url", "bait1", "bait2"])
        ids = {key: obj.pk for key, obj in old_catches.items()}
        prior = {w.catch_id: w for w in WeeklyCatchRegion.objects.filter(region=region, catch_id__in=ids.values())}
        new_links = []
        updates = []
        for pk in ids.values():
            link = prior.get(pk)
            if link is None:
                new_links.append(WeeklyCatchRegion(catch_id=pk, region=region, first_seen_at=when, last_seen_at=when))
            elif link.last_seen_at < when:
                link.last_seen_at = when
                updates.append(link)
        WeeklyCatchRegion.objects.bulk_create(new_links)
        if updates:
            WeeklyCatchRegion.objects.bulk_update(updates, ["last_seen_at"])
    return {"region": region, "total": len(records), "new": len(unseen), "duplicate_in_source": len(collisions), "duplicates": collisions, "collection_id": collection.pk if collection else None,
            "unmatched_fish": sorted({r["fish"] for r in distinct.values() if r["fish"].strip().casefold() not in fish_map}),
            "unmatched_waterbodies": sorted({r["waterbody"] for r in distinct.values() if r["waterbody"].strip().casefold() not in wb_map})}

"""Audit unresolved Fish/Waterbody foreign keys in weekly records.

Usage:
    python manage.py audit_record_links
    python manage.py audit_record_links --relink
    python manage.py audit_record_links --output-dir record-logs/quality
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from fish.models import Fish
from waterbodies.models import Waterbody
from records.models import Catch


def normalize_name(value):
    """Conservative normalization: trim/casefold/normalize whitespace only."""
    return " ".join((value or "").split()).casefold()


def name_lookup(model):
    """Return unique matches and ambiguous names (do not guess between matches)."""
    found = defaultdict(list)
    for pk, name in model.objects.values_list("pk", "name"):
        found[normalize_name(name)].append((pk, name))
    unique = {key: rows[0] for key, rows in found.items() if key and len(rows) == 1}
    ambiguous = {key: rows for key, rows in found.items() if key and len(rows) > 1}
    return unique, ambiguous


def summarize_field(name_field, fk_field, lookup, ambiguous):
    rows = list(
        Catch.objects.filter(**{f"{fk_field}__isnull": True})
        .values(name_field).annotate(count=Count("id"))
        .order_by("-count", name_field)
    )
    result = []
    for row in rows:
        source = row[name_field] or ""
        norm = normalize_name(source)
        match = lookup.get(norm)
        status = "ambiguous" if norm in ambiguous else ("exact_match" if match else "not_found")
        result.append({
            "source_name": source,
            "catches": row["count"],
            "status": status,
            "suggested_id": match[0] if match else None,
            "suggested_name": match[1] if match else "",
        })
    return result


def csv_write(path, rows):
    fields = ["source_name", "catches", "status", "suggested_id", "suggested_name"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


class Command(BaseCommand):
    help = "Audit Fish/Waterbody links in collected records and optionally relink exact name matches."

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", default="record-logs/quality", help="Directory for JSON and CSV reports")
        parser.add_argument("--relink", action="store_true", help="Fill missing FKs by unambiguous, normalized exact name (never overwrite existing links)")

    def handle(self, *args, **options):
        out_dir = Path(options["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        fish_lookup, ambiguous_fish = name_lookup(Fish)
        waterbody_lookup, ambiguous_wb = name_lookup(Waterbody)

        updated_fish = updated_wb = 0
        if options["relink"]:
            # Only fill NULL links; never change names, delete catches, or create catalog entries.
            # Iterate aggregated names to avoid loading every Catch object.
            with transaction.atomic():
                for raw in Catch.objects.filter(fish__isnull=True).values_list("fish_name", flat=True).distinct():
                    match = fish_lookup.get(normalize_name(raw))
                    if match:
                        updated_fish += Catch.objects.filter(fish__isnull=True, fish_name=raw).update(fish_id=match[0])
                for raw in Catch.objects.filter(waterbody__isnull=True).values_list("waterbody_name", flat=True).distinct():
                    match = waterbody_lookup.get(normalize_name(raw))
                    if match:
                        updated_wb += Catch.objects.filter(waterbody__isnull=True, waterbody_name=raw).update(waterbody_id=match[0])

        totals = Catch.objects.aggregate(
            total=Count("id"),
            fish_linked=Count("id", filter=Q(fish__isnull=False)),
            waterbody_linked=Count("id", filter=Q(waterbody__isnull=False)),
            both_linked=Count("id", filter=Q(fish__isnull=False, waterbody__isnull=False)),
        )
        fish_rows = summarize_field("fish_name", "fish", fish_lookup, ambiguous_fish)
        wb_rows = summarize_field("waterbody_name", "waterbody", waterbody_lookup, ambiguous_wb)
        total = totals["total"] or 0
        report = {
            "generated_at": timezone.now().isoformat(),
            "relink_enabled": bool(options["relink"]),
            "relinked": {"fish": updated_fish, "waterbodies": updated_wb},
            "catches": {
                "total": total,
                "fish_linked": totals["fish_linked"],
                "fish_unlinked": total - totals["fish_linked"],
                "waterbody_linked": totals["waterbody_linked"],
                "waterbody_unlinked": total - totals["waterbody_linked"],
                "both_linked": totals["both_linked"],
            },
            "unmatched_fish": fish_rows,
            "unmatched_waterbodies": wb_rows,
            "ambiguous_catalog_fish": {k: v for k, v in ambiguous_fish.items()},
            "ambiguous_catalog_waterbodies": {k: v for k, v in ambiguous_wb.items()},
        }
        (out_dir / "record-links.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        csv_write(out_dir / "unmatched-fish.csv", fish_rows)
        csv_write(out_dir / "unmatched-waterbodies.csv", wb_rows)

        self.stdout.write(f"[catches] total={total} fish_linked={totals['fish_linked']} fish_unlinked={total - totals['fish_linked']}")
        self.stdout.write(f"[waterbodies] linked={totals['waterbody_linked']} unlinked={total - totals['waterbody_linked']} both_linked={totals['both_linked']}")
        self.stdout.write(f"[unmatched names] fish={len(fish_rows)} waterbodies={len(wb_rows)}")
        if options["relink"]:
            self.stdout.write(self.style.SUCCESS(f"[relinked] fish={updated_fish} waterbodies={updated_wb}"))
        self.stdout.write(f"[report] {out_dir.resolve()}")

"""One-time migration of accumulated WEEKLY catches from test project's SQLite DB."""
import sqlite3
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone as dt_timezone
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from records.services import import_weekly
from records.models import Catch


class Command(BaseCommand):
    help = "Import weekly catches from rf4-records-test v6.1 SQLite without modifying source DB."

    def add_arguments(self, parser):
        parser.add_argument("--sqlite", required=True, help="Path to test project's output/records.sqlite3")

    def handle(self, *args, **opts):
        path = Path(opts["sqlite"])
        if not path.is_file():
            raise CommandError(f"File not found: {path}")
        db = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'catches', 'weekly_catch_regions'}.issubset(tables):
                raise CommandError("Expected v6 SQLite tables catches and weekly_catch_regions")
            regions = [r[0] for r in db.execute("SELECT DISTINCT region FROM weekly_catch_regions ORDER BY region")]
            total_new = 0
            for region in regions:
                rows = db.execute("""
                    SELECT c.*, w.first_seen_at AS weekly_first_seen, w.last_seen_at AS weekly_last_seen
                    FROM catches c JOIN weekly_catch_regions w ON w.catch_id = c.id
                    WHERE w.region=? ORDER BY c.id
                """, (region,)).fetchall()
                if not rows:
                    continue
                records = [{"fish": r["fish"], "waterbody": r["waterbody"], "bait": r["bait"],
                            "weight_g": r["weight_g"], "player": r["player"], "caught_date": r["caught_date"],
                            "fish_icon_url": r["fish_icon_url"], "bait_icon_url": r["bait_icon_url"], "rank": 1}
                           for r in rows]
                payload = {"source_url": f"https://rf4game.ru/records/weekly/region/{region}/",
                           "record_count": len(records), "fish_group_count": len({r['fish'] for r in records}),
                           "warnings": [], "records": records}
                result = import_weekly(payload)
                total_new += result["new"]
                self.stdout.write(f"[{region}] imported {len(records)}, new {result['new']}")
            # Restore per-catch historical first/last timestamps as available.
            # A record can be shared by multiple regions. min(first), max(last).
            history = db.execute("""
                SELECT c.fingerprint, MIN(c.first_seen_at) AS first_seen,
                       MAX(c.last_seen_at) AS last_seen
                FROM catches c JOIN weekly_catch_regions w ON w.catch_id=c.id
                GROUP BY c.id
            """).fetchall()
            for h in history:
                try:
                    first = datetime.fromisoformat(h["first_seen"])
                    last = datetime.fromisoformat(h["last_seen"])
                    if timezone.is_naive(first): first = first.replace(tzinfo=dt_timezone.utc)
                    if timezone.is_naive(last): last = last.replace(tzinfo=dt_timezone.utc)
                    Catch.objects.filter(fingerprint=h["fingerprint"]).update(first_seen_at=first, last_seen_at=last)
                except (TypeError, ValueError):
                    pass
            self.stdout.write(self.style.SUCCESS(f"Complete: {total_new} new distinct weekly catches"))
        finally:
            db.close()

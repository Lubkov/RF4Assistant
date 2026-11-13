import csv
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from records.analytics import report


class Command(BaseCommand):
    help = "Export weekly catches grouped by waterbody, fish and combined bait (CSV and JSON)."

    def add_arguments(self, parser):
        parser.add_argument("--date-from", required=True)
        parser.add_argument("--date-to", required=True)
        parser.add_argument("--region", default="ALL")
        parser.add_argument("--waterbody-id", type=int)
        parser.add_argument("--fish-id", type=int)
        parser.add_argument("--output", default=None)

    def handle(self, *args, **opts):
        try:
            result = report(date_from=opts["date_from"], date_to=opts["date_to"], region=opts["region"],
                            waterbody_id=opts["waterbody_id"], fish_id=opts["fish_id"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        output = Path(opts["output"] or (settings.BASE_DIR / "record-reports"))
        output.mkdir(parents=True, exist_ok=True)
        (output / "weekly-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        with (output / "weekly-report.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Водоём", "Рыба", "Макс. вес (г)", "Количество", "Наживки"])
            for row in result["rows"]:
                writer.writerow([row["waterbody"], row["fish"], row["max_weight_g"], row["record_count"],
                                 ", ".join(f"{b['bait']} {b['count']}" for b in row["baits"])])
        self.stdout.write(f"[report] unique={result['total_unique_catches']} groups={result['total_groups']} output={output}")

import json
import time
from django.core.management.base import BaseCommand, CommandError
from records.sources import REGION_NAMES
from records.worker import run_weekly


class Command(BaseCommand):
    help = "Collect RF4 weekly regional records in a separate worker process; --loop repeats at intervals."

    def add_arguments(self, parser):
        parser.add_argument("--regions", nargs="+", choices=list(REGION_NAMES))
        parser.add_argument("--headful", action="store_true", help="Show Chromium for debugging")
        parser.add_argument("--interval-minutes", type=int, default=15)
        parser.add_argument("--loop", action="store_true", help="Keep polling (run as a separate process)")

    def handle(self, *args, **options):
        minutes = options["interval_minutes"]
        if minutes < 5:
            raise CommandError("Minimum interval is 5 minutes")
        while True:
            try:
                result = run_weekly(regions=options["regions"], headless=not options["headful"])
                for item in result["processed"]:
                    self.stdout.write(f"[ok] {item['region']}: {item['total']} records, {item['new']} new")
                for item in result["errors"]:
                    self.stderr.write(f"[error] {item['region']}: {item['error']}")
                self.stdout.write(f"[summary] sources={len(result['processed'])} errors={len(result['errors'])}")
            except Exception as exc:
                self.stderr.write(f"[error] collection failed: {exc}")
                if not options["loop"]:
                    raise CommandError(str(exc)) from exc
            if not options["loop"]:
                if result["errors"]:
                    raise CommandError("Some regional sources failed; see record-logs/last-run.json")
                return
            try:
                time.sleep(minutes * 60)
            except KeyboardInterrupt:
                self.stdout.write("Stopped")
                return

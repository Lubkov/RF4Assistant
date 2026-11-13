"""Collector runs in its OWN OS process, not inside Django's HTTP server."""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from playwright.sync_api import sync_playwright
from django.conf import settings
from django.db import close_old_connections, connections
from .parser import parse_records
from .sources import TYPES, REGION_NAMES, discover_sources
from .services import import_weekly
from .icons import fill_missing_icons

logger = logging.getLogger(__name__)


def _import_weekly_in_db_thread(payload):
    """Run Django's synchronous ORM outside Playwright's event-loop thread."""
    close_old_connections()
    try:
        return import_weekly(payload)
    finally:
        # DB connections are thread-local and must not leak across jobs.
        connections.close_all()


def run_weekly(*, regions=None, headless=True, timeout=45, output=None):
    output = Path(output or settings.BASE_DIR / "record-logs")
    output.mkdir(exist_ok=True, parents=True)
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="records-db") as db_executor, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            page = browser.new_page(locale="ru-RU")
            def load(url):
                response = page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                page.locator(".records.flex_table").first.wait_for(state="attached", timeout=int(timeout * 1000))
                if response and response.status >= 400:
                    raise ValueError(f"HTTP {response.status}")
                return page.content(), page.url
            html, _ = load(TYPES["weekly"])
            sources = discover_sources(html, "weekly")
            if not sources:
                raise ValueError("No region links found: the page may be blocked")
            if regions:
                missing = set(regions) - {s.region for s in sources}
                if missing:
                    raise ValueError(f"Missing requested regions: {sorted(missing)}")
                sources = [s for s in sources if s.region in regions]
            for source in sources:
                try:
                    html, actual_url = load(source.url)
                    if actual_url.rstrip("/") != source.url.rstrip("/"):
                        raise ValueError(f"Redirected to unexpected page: {actual_url}")
                    payload = parse_records(html, actual_url)
                    result = db_executor.submit(_import_weekly_in_db_thread, payload).result()
                    results.append(result)
                    logger.info("%s: %s records, %s new", source.region, result["total"], result["new"])
                    if result["duplicates"]:
                        (output / f"weekly_{source.region.lower()}_duplicates.json").write_text(json.dumps(result["duplicates"], ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as exc:
                    errors.append({"region": source.region, "error": str(exc)})
                    logger.exception("Failed to collect %s", source.region)
            # Image fetching is best-effort and runs in the DB worker, never
            # in Django's web-server process or Playwright's event-loop thread.
            try:
                icon_stats = fill_missing_icons(page, db_executor, failure_cache=output / "icon-failures.json")
                logger.info("RF4 icons: %s", icon_stats)
            except Exception:
                logger.exception("Icon enrichment failed; catches remain saved")
        finally:
            browser.close()
    result = {"processed": results, "errors": errors}
    (output / "last-run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

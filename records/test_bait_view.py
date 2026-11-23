"""Regression tests for the alternative weekly statistics grouping."""
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from waterbodies.models import Waterbody

from .analytics import bait_report, report
from .services import import_weekly


class BaitViewTests(TestCase):
    def setUp(self):
        records = [
            {"fish": "Вьюн", "waterbody": "р. Сура", "weight_g": 283,
             "player": "p1", "caught_date": "2026-11-11", "bait": "Мотыль; Опарыш", "rank": 1},
            {"fish": "Вьюн", "waterbody": "р. Сура", "weight_g": 270,
             "player": "p2", "caught_date": "2026-11-11", "bait": "Опарыш; Мотыль", "rank": 2},
            {"fish": "Ерш", "waterbody": "р. Сура", "weight_g": 120,
             "player": "p3", "caught_date": "2026-11-11", "bait": "Мотыль; Опарыш", "rank": 1},
            {"fish": "Вьюн", "waterbody": "р. Сура", "weight_g": 320,
             "player": "p4", "caught_date": "2026-11-11", "bait": "Мотыль", "rank": 3},
        ]
        self.payload = {"source_url": "https://rf4game.ru/records/weekly/region/RU/",
                        "fish_group_count": 2, "record_count": 4,
                        "records": records, "warnings": []}
        import_weekly(self.payload)

    def test_group_by_combination_and_fish(self):
        data = bait_report(date_from="2026-11-11", date_to="2026-11-11")
        self.assertEqual(data["total_unique_catches"], 4)
        rows = {row["bait"]: row for row in data["rows"]}
        combo = rows["Мотыль и Опарыш"]
        self.assertEqual(combo["record_count"], 3)
        self.assertEqual(combo["max_weight_g"], 283)
        self.assertEqual([(f["fish"], f["count"]) for f in combo["fish_details"]],
                         [("Вьюн", 2), ("Ерш", 1)])
        self.assertEqual(
            [(f["average_weight_display"], f["max_weight_g"]) for f in combo["fish_details"]],
            [("276 г", 283), ("120 г", 120)],
        )
        self.assertEqual(
            [[catch["player"] for catch in fish["catches"]] for fish in combo["fish_details"]],
            [["p1", "p2"], ["p3"]],
        )
        self.assertEqual(rows["Мотыль"]["record_count"], 1)
        self.assertEqual(sum(f["count"] for row in data["rows"] for f in row["fish_details"]), 4)

    def test_region_does_not_double_count(self):
        gl = dict(self.payload, source_url="https://rf4game.ru/records/weekly/region/GL/")
        import_weekly(gl)
        data = bait_report(date_from="2026-11-11", date_to="2026-11-11", region="ALL")
        self.assertEqual(data["total_unique_catches"], 4)

    def test_fish_report_groups_reversed_combination(self):
        data = report(date_from="2026-11-11", date_to="2026-11-11")
        row = next(row for row in data["rows"] if row["fish"] == "Вьюн")
        self.assertEqual(row["baits"], [
            {"bait": "Мотыль и Опарыш", "count": 2},
            {"bait": "Мотыль", "count": 1},
        ])

    def test_view_tabs_and_preserved_filters(self):
        waterbody = Waterbody.objects.get(name="р. Сура")
        with patch("records.views.timezone.localdate", return_value=date(2026, 11, 13)):
            response = self.client.get("/records/", {
                "view": "bait", "days": "3", "region": "ALL", "waterbody_id": waterbody.pk,
                "sort": "weight",
            })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "По наживкам")
        self.assertContains(response, "Мотыль и Опарыш")
        self.assertContains(response, '<th scope="col" class="align-middle text-nowrap">Виды рыбы</th>', html=True)
        self.assertContains(response, 'data-bs-target="#bait-records-panel"', count=5)
        self.assertNotContains(response, "records-bait-more")
        self.assertContains(response, 'id="bait-records-details" hidden')
        self.assertContains(response, 'data-caught-date="2026-11-11"', count=4)
        self.assertContains(response, "276 г")
        self.assertEqual([row["record_count"] for row in response.context["data"]["rows"]], [3, 1])
        self.assertNotIn("sort=", response.context["view_urls"]["bait"])
        self.assertIn("view=fish", response.context["view_urls"]["fish"])
        self.assertIn("days=3", response.context["view_urls"]["fish"])

    def test_bait_preview_shows_three_species_and_counts_the_rest(self):
        records = [
            dict(self.payload["records"][2], fish=fish, weight_g=weight)
            for fish, weight in (("Карп", 90), ("Линь", 80), ("Лещ", 70))
        ]
        import_weekly(dict(self.payload, records=records, record_count=len(records)))
        waterbody = Waterbody.objects.get(name="р. Сура")
        with patch("records.views.timezone.localdate", return_value=date(2026, 11, 11)):
            response = self.client.get("/records/", {"view": "bait", "waterbody_id": waterbody.pk})
        row = response.context["data"]["rows"][0]
        self.assertEqual([fish["fish"] for fish in row["fish_preview"]], ["Вьюн", "Ерш", "Карп"])
        self.assertContains(response, ">+2</button>")
        self.assertContains(response, 'data-bs-target="#bait-records-panel"', count=7)
        self.assertContains(response, 'data-bait-fish-name>Линь</span>')
        self.assertContains(response, 'data-bait-fish-name>Лещ</span>')

    def test_pagination_limits_rows_and_preserves_filters_for_both_tabs(self):
        records = [
            dict(self.payload["records"][0], fish=f"Species {i:02}", bait=f"Bait {i:02}", weight_g=i)
            for i in range(1, 24)
        ]
        import_weekly(dict(self.payload, records=records, record_count=len(records)))
        waterbody = Waterbody.objects.get(name="р. Сура")
        with patch("records.views.timezone.localdate", return_value=date(2026, 11, 12)):
            for view in ("fish", "bait"):
                with self.subTest(view=view):
                    filters = {"view": view, "days": 2, "region": "RU", "waterbody_id": waterbody.pk}
                    if view == "fish":
                        filters["sort"] = "weight"
                    first = self.client.get("/records/", filters)
                    second = self.client.get("/records/", {**filters, "page": 2})
                    self.assertEqual(len(first.context["page_groups"][0]["rows"]), 20)
                    self.assertEqual(len(second.context["page_groups"][0]["rows"]), 5)
                    visible_rows = first.context["page_obj"].object_list + second.context["page_obj"].object_list
                    self.assertEqual(
                        [row[view] for row in visible_rows],
                        [row[view] for row in first.context["data"]["rows"]],
                    )
                    query = "&amp;".join(f"{key}={value}" for key, value in filters.items())
                    self.assertContains(first, f'href="?{query}&amp;page=2"')
                    self.assertNotIn("page=", second.context["view_urls"]["fish"])
                    self.assertNotIn("page=", second.context["view_urls"]["bait"])
                    if view == "fish":
                        details = self.client.get(second.context["page_obj"][0]["details_url"])
                        self.assertEqual(details.status_code, 200)
                    else:
                        self.assertContains(second, "data-bait-fish-summary", count=5)

    def test_invalid_view(self):
        self.assertEqual(self.client.get("/records/", {"view": "unknown"}).status_code, 400)

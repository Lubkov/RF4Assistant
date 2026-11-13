"""Regression tests for the alternative weekly statistics grouping."""
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from .analytics import bait_report
from .services import import_weekly


class BaitViewTests(TestCase):
    def setUp(self):
        records = [
            {"fish": "Вьюн", "waterbody": "р. Сура", "weight_g": 283,
             "player": "p1", "caught_date": "2026-11-11", "bait": "Мотыль; Опарыш", "rank": 1},
            {"fish": "Вьюн", "waterbody": "р. Сура", "weight_g": 270,
             "player": "p2", "caught_date": "2026-11-11", "bait": "Мотыль; Опарыш", "rank": 2},
            {"fish": "Ерш", "waterbody": "р. Сура", "weight_g": 120,
             "player": "p3", "caught_date": "2026-11-11", "bait": "Мотыль; Опарыш", "rank": 1},
            {"fish": "Вьюн", "waterbody": "р. Сура", "weight_g": 220,
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
        self.assertEqual(rows["Мотыль"]["record_count"], 1)
        self.assertEqual(sum(f["count"] for row in data["rows"] for f in row["fish_details"]), 4)

    def test_region_does_not_double_count(self):
        gl = dict(self.payload, source_url="https://rf4game.ru/records/weekly/region/GL/")
        import_weekly(gl)
        data = bait_report(date_from="2026-11-11", date_to="2026-11-11", region="ALL")
        self.assertEqual(data["total_unique_catches"], 4)

    def test_view_tabs_and_preserved_filters(self):
        from datetime import date
        with patch("records.views.timezone.localdate", return_value=date(2026, 11, 13)):
            response = self.client.get("/records/", {"view": "bait", "days": "3", "region": "ALL"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "По наживкам")
        self.assertContains(response, "Мотыль и Опарыш")
        self.assertContains(response, "Виды рыб")
        self.assertIn("view=fish", response.context["view_urls"]["fish"])
        self.assertIn("days=3", response.context["view_urls"]["fish"])

    def test_invalid_view(self):
        self.assertEqual(self.client.get("/records/", {"view": "unknown"}).status_code, 400)

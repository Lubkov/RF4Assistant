from datetime import date
from django.test import TestCase
from django.utils import timezone
from fish.models import Fish
from waterbodies.models import Waterbody
from .models import Bait, Collection, Catch, WeeklyCatchRegion
from .bait_utils import split_baits
from .services import import_weekly
from .analytics import report


class WeeklyImportTests(TestCase):
    def make_payload(self, region="RU", bait="Мотыль; Опарыш"):
        r = {"fish": "Вьюн", "waterbody": "Сура", "weight_g": 283, "player": "tester",
             "caught_date": "2026-11-11", "bait": bait, "rank": 1}
        return {"source_url": f"https://rf4game.ru/records/weekly/region/{region}/",
                "fish_group_count": 1, "record_count": 1, "records": [r], "warnings": []}

    def test_idempotent_and_bait_combination(self):
        result = import_weekly(self.make_payload())
        self.assertEqual(result["new"], 1)
        self.assertEqual(import_weekly(self.make_payload())["new"], 0)
        self.assertEqual(Collection.objects.count(), 1)
        self.assertEqual(Catch.objects.count(), 1)
        stats = report(date_from="2026-11-11", date_to="2026-11-11")
        self.assertEqual(stats["total_unique_catches"], 1)
        self.assertEqual(stats["rows"][0]["baits"], [{"bait": "Мотыль и Опарыш", "count": 1}])

    def test_cross_region_no_duplicate(self):
        import_weekly(self.make_payload("RU"))
        self.assertEqual(import_weekly(self.make_payload("GL"))["new"], 0)
        self.assertEqual(Catch.objects.count(), 1)
        self.assertEqual(WeeklyCatchRegion.objects.count(), 2)
        self.assertEqual(report(date_from="2026-11-11", date_to="2026-11-11")["total_unique_catches"], 1)

    def test_links_to_catalog(self):
        self.assertTrue(Fish.objects.filter(name="Вьюн").exists())
        self.assertTrue(Waterbody.objects.filter(name="р. Сура").exists())
        payload = self.make_payload()
        payload["records"][0]["waterbody"] = "р. Сура"
        import_weekly(payload)
        catch = Catch.objects.get()
        self.assertIsNotNone(catch.fish_id)
        self.assertIsNotNone(catch.waterbody_id)


class BaitCatalogTests(TestCase):
    def test_two_baits_are_two_foreign_keys(self):
        payload = WeeklyImportTests().make_payload(bait="Мотыль; Опарыш")
        import_weekly(payload)
        item = Catch.objects.get()
        self.assertEqual(item.bait1.name, "Мотыль")
        self.assertEqual(item.bait2.name, "Опарыш")
        self.assertEqual(Bait.objects.count(), 2)
        self.assertEqual(import_weekly(payload)["new"], 0)
        self.assertEqual(Bait.objects.count(), 2)

    def test_same_bait_twice(self):
        import_weekly(WeeklyImportTests().make_payload(bait="Муха; Муха"))
        item = Catch.objects.get()
        self.assertEqual(item.bait1_id, item.bait2_id)
        self.assertEqual(Bait.objects.count(), 1)

    def test_no_baits(self):
        import_weekly(WeeklyImportTests().make_payload(bait=""))
        item = Catch.objects.get()
        self.assertIsNone(item.bait1_id)
        self.assertIsNone(item.bait2_id)

    def test_invalid_three_baits_rejected(self):
        with self.assertRaises(ValueError):
            split_baits("A; B; C")

class WeeklyReportPageTests(TestCase):
    def test_default_page_and_sort_filters(self):
        response = self.client.get('/records/', {'date_from': '2026-11-10', 'date_to': '2026-11-11'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Статистика недельных рекордов')
        self.assertContains(response, 'data-record-days="7"')

    def test_icons_and_bait_combination_render(self):
        import_weekly(WeeklyImportTests().make_payload())
        catch = Catch.objects.get()
        # Assign stored paths; test does not require files to exist on disk.
        f = Fish.objects.get(name='Вьюн')
        f.image = 'fish/icons/sample.webp'
        f.save(update_fields=['image'])
        first = catch.bait1
        first.image = 'baits/sample.webp'
        first.save(update_fields=['image'])
        response = self.client.get('/records/', {
            'date_from': '2026-11-11', 'date_to': '2026-11-11', 'sort': 'weight',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Мотыль и Опарыш')
        self.assertContains(response, 'fish/icons/sample.webp')
        self.assertContains(response, 'baits/sample.webp')
        self.assertEqual(response.context['data']['total_unique_catches'], 1)
        self.assertEqual(sum(b['count'] for b in response.context['data']['rows'][0]['baits']), 1)

    def test_bad_sort_is_rejected(self):
        response = self.client.get('/records/', {
            'date_from': '2026-11-11', 'date_to': '2026-11-11', 'sort': 'invalid',
        })
        self.assertEqual(response.status_code, 400)

from django.test import TestCase

from .models import Waterbody


class WaterbodySeedTests(TestCase):
    def test_initial_data(self):
        self.assertEqual(Waterbody.objects.count(), 18)
        first = Waterbody.objects.get(pk=1)
        self.assertEqual((first.name, first.level, first.slug), ("оз. Комариное", 1, "komarinoe"))
        self.assertEqual(Waterbody.objects.get(pk=18).name, "Норвежское море")
        self.assertEqual(list(Waterbody.objects.values_list("id", flat=True).order_by("level", "id"))[:3], [1, 2, 3])

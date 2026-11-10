from django.db import IntegrityError, transaction
from django.test import TestCase

from waterbodies.models import Waterbody
from .models import Fish, WaterbodyFish


class FishSeedTests(TestCase):
    def test_initial_data(self):
        self.assertEqual(Fish.objects.count(), 251)
        self.assertEqual(Fish.objects.get(pk=105).name, "Лещ")
        self.assertEqual(Fish.objects.get(pk=154).super_trophy_weight, None)
        self.assertEqual(Fish.objects.get(pk=240).super_trophy_weight, None)
        self.assertEqual(Fish.objects.filter(super_trophy_weight__isnull=True).count(), 2)
        self.assertEqual(WaterbodyFish.objects.count(), 0)

    def test_rarity_labels(self):
        self.assertEqual(Fish.Rarity.COMMON.label, "Обычная")
        self.assertEqual(Fish.Rarity.RARE.label, "Редкая")
        self.assertEqual(Fish.Rarity.VERY_RARE.label, "Очень редкая")

    def test_duplicate_waterbody_fish_is_rejected(self):
        waterbody = Waterbody.objects.get(pk=1)
        fish = Fish.objects.get(pk=105)
        WaterbodyFish.objects.create(waterbody=waterbody, fish=fish)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WaterbodyFish.objects.create(waterbody=waterbody, fish=fish)

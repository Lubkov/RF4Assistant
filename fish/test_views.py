from django.test import TestCase
from django.urls import reverse

from .models import Fish


class FishListPageTests(TestCase):
    def test_fish_list_shows_active_fish_and_weights(self):
        Fish.objects.create(name="Тестовая рыба", trophy_weight=4400, super_trophy_weight=7000, rarity=2)
        Fish.objects.create(name="Скрытая рыба", trophy_weight=500, rarity=1, is_active=False)
        Fish.objects.create(name="Без редкого трофея", trophy_weight=650, super_trophy_weight=None, rarity=3)
        response = self.client.get(reverse("fish:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Справочник видов рыб в Russian Fishing 4")
        self.assertContains(response, "Тестовая рыба")
        self.assertNotContains(response, "Скрытая рыба")
        self.assertContains(response, "Вес редкого трофея")
        self.assertContains(response, 'data-grams="4400"')
        self.assertContains(response, "Редкий вид")
        self.assertContains(response, "Редчайший вид")

    def test_fish_navigation_link(self):
        response = self.client.get(reverse("fish:list"))
        self.assertContains(response, 'href="/fish/"')
        self.assertContains(response, 'Справочник</button>')
        self.assertContains(response, 'Виды рыб</a>')

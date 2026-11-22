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
        self.assertContains(response, '<span>Справочники</span>')
        self.assertContains(response, '<span>Виды рыб</span>')

    def test_fish_icons_and_rarity_icons_are_in_the_correct_columns(self):
        with_icon = Fish.objects.create(name="С иконкой", trophy_weight=1000, rarity=2)
        with_icon.image = "fish/icons/example.webp"
        with_icon.save(update_fields=["image"])
        Fish.objects.create(name="Без иконки", trophy_weight=2000, rarity=3)

        response = self.client.get(reverse("fish:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/media/fish/icons/example.webp')
        self.assertContains(response, 'fish-list-icon-placeholder')
        self.assertNotContains(response, 'fish-name-rarity')

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")
        rows = soup.select("#fish-table-body tr")
        row_with_icon = next(row for row in rows if row["data-name"] == "с иконкой")
        name_cell, _, _, rarity_cell = row_with_icon.select("td")
        self.assertIn("/media/fish/icons/example.webp", name_cell.select_one("img")["src"])
        self.assertFalse(name_cell.select("img.rarity-icon"))
        self.assertIn("rarity-2.svg", rarity_cell.select_one("img")["src"])
        row_without_icon = next(row for row in rows if row["data-name"] == "без иконки")
        self.assertIsNotNone(row_without_icon.select_one("td .fish-list-icon-placeholder"))
        self.assertIn("rarity-3.svg", row_without_icon.select("td")[3].select_one("img")["src"])

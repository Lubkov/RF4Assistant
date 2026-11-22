from django.test import TestCase
from django.urls import reverse

from waterbodies.models import Waterbody


class HomePageTests(TestCase):
    def test_home_renders_and_has_bootstrap(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'RF4 Assistant')
        self.assertContains(response, 'bootstrap@5.3.3')
        self.assertContains(response, 'data-bs-theme="dark"')

    def test_home_shows_only_active_waterbodies_in_level_order(self):
        low = Waterbody.objects.create(name='Нижний уровень', slug='low', level=1)
        high = Waterbody.objects.create(name='Верхний уровень', slug='high', level=20)
        Waterbody.objects.create(name='Скрытый водоём', slug='hidden', level=1, is_active=False)
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, low.name)
        self.assertContains(response, high.name)
        self.assertNotContains(response, 'Скрытый водоём')
        self.assertLess(response.content.index(low.name.encode()), response.content.index(high.name.encode()))
        self.assertContains(response, f'#waterbody-{low.pk}')
        self.assertContains(response, 'waterbody-placeholder.svg')

    def test_uploaded_image_is_used_for_card(self):
        Waterbody.objects.create(name='С картинкой', slug='with-image', level=1, image='waterbodies/test.webp')
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, '/media/waterbodies/test.webp')


class ShopPricesTests(TestCase):
    def test_shop_prices_page_and_navigation(self):
        from bs4 import BeautifulSoup

        url = reverse("core:shop_prices")
        home = BeautifulSoup(self.client.get(reverse("core:home")).content, "html.parser")
        link = home.select_one(f'nav a[href="{url}"]')
        self.assertEqual(link.get_text(strip=True), "Цены в магазинах")
        self.assertIsNotNone(link.find("svg"))

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        page = BeautifulSoup(response.content, "html.parser")
        self.assertIsNotNone(page.select_one(f'nav a[href="{url}"][aria-current="page"]'))
        main_table, branded_table = page.select("main table")
        headings = [cell.get_text(strip=True) for cell in main_table.select("thead th")]
        self.assertEqual(len(headings), 6)
        self.assertNotIn("Фирменный магазин", headings)
        self.assertNotIn("Фирменная мастерская", headings)
        rows = main_table.select("tbody tr")
        self.assertEqual(len(rows), 18)
        self.assertCountEqual(
            [row.th.get_text(strip=True) for row in rows],
            [label.get_text(strip=True) for label in page.select(".map-dropdown a span")],
        )
        self.assertTrue(all(len(row.select("td")) == 5 for row in rows))
        for row in rows:
            for cell in row.select("td"):
                self.assertRegex(cell.get_text(strip=True), r"^(?:\d+%|—)$")
        self.assertEqual(rows[0].get_text(" ", strip=True), "оз. Комариное 100% 100% 100% 100% 90%")
        self.assertEqual(rows[-1].get_text(" ", strip=True), "Норвежское море 120% 100% 150% 116% 200%")
        self.assertEqual(
            [row.get_text(" ", strip=True) for row in branded_table.select("tbody tr")],
            [
                "Фирменный магазин Zeiman оз. Янтарное 100% 81%",
                "Фирменный магазин Beluga Ладожское оз. 100% 81%",
            ],
        )


class MapDropdownTests(TestCase):
    def test_waterbody_menu_shows_access_levels(self):
        Waterbody.objects.create(name='Тестовое озеро', slug='test-lake', level=7)
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, '<small class="map-dropdown-level text-body-secondary">7 ур.</small>', html=False)
        self.assertContains(response, 'Тестовое озеро')

    def test_map_menu_uses_column_first_grid(self):
        from django.conf import settings
        css = (settings.BASE_DIR / 'static/css/site.css').read_text(encoding='utf-8')
        self.assertIn('grid-template-rows: repeat(9, auto)', css)
        self.assertIn('grid-auto-flow: column', css)

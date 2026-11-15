"""Navigation for the two weekly records groupings."""
from django.test import TestCase
from django.urls import reverse


class RecordsNavigationTests(TestCase):
    def test_main_menu_has_dropdown_not_records_link(self):
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, '<span>Рекорды</span>', html=False)
        self.assertContains(response, 'data-bs-toggle="dropdown"')
        self.assertContains(response, 'href="/records/?view=fish"')
        self.assertContains(response, 'href="/records/?view=bait"')
        self.assertContains(response, 'Рекорды по видам рыб')
        self.assertContains(response, 'Рекорды по наживкам')

    def test_each_menu_link_selects_right_tab(self):
        for view in ('fish', 'bait'):
            with self.subTest(view=view):
                response = self.client.get(reverse('records:weekly'), {'view': view})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['selected_view'], view)
                self.assertContains(response, 'Статистика недельных рекордов')
                self.assertContains(response, 'По видам рыб')
                self.assertContains(response, 'По наживкам')
                self.assertContains(response, 'heading-icon')
                self.assertContains(response, f'href="/records/?view={view}"')

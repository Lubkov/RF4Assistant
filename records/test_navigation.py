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
                self.assertContains(response, 'M8 21h8m-4-4v4')
                self.assertContains(response, 'nav nav-tabs mb-3')
                self.assertContains(response, "with kind='fish'" if False else 'M3 7h4m-4 5h4m-4 5h4')
                self.assertContains(response, 'M4 5h9M4 10h7M4 15h5')
                self.assertContains(response, f'href="/records/?view={view}"')

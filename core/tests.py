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

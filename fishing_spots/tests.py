import json
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from fish.models import Fish, WaterbodyFish
from waterbodies.models import Waterbody, WaterbodyMap
from .models import FishingSpot, FishingSpotScreenshot, FishingSpotCategory


def screenshot(index):
    buffer = BytesIO()
    Image.new('RGB', (30, 20), (index * 20, 30, 50)).save(buffer, 'PNG')
    return SimpleUploadedFile(f'{index}.png', buffer.getvalue(), content_type='image/png')


class WizardTests(TestCase):
    def setUp(self):
        self.dir = TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.dir.name)
        self.media.enable()
        self.addCleanup(self.media.disable)
        self.body = Waterbody.objects.get(pk=1)
        self.game_map = WaterbodyMap.objects.create(
            waterbody=self.body, game_x_min=0, game_x_max=100,
            game_y_min=0, game_y_max=100,
        )
        self.game_map.image.save('test-map.png', ContentFile(b'map'), save=True)
        self.fish = Fish.objects.get(pk=105)
        WaterbodyFish.objects.get_or_create(waterbody=self.body, fish=self.fish)

    def payload(self):
        return {
            'categories': json.dumps(['farm', 'trophy']),
            'waterbody_id': str(self.body.pk),
            'coordinates': '33:44',
            'is_mixed_fish': 'false',
            'fish_ids': json.dumps([self.fish.pk]),
            'depth_cm': '250',
            'screenshots': [screenshot(i) for i in range(4)],
        }

    def test_wizard_is_globally_available(self):
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'id="spot-modal"')
        self.assertContains(response, 'Новое место ловли')

    def test_options_provide_calibration_and_fish(self):
        response = self.client.get(reverse('fishing_spots:options'))
        self.assertEqual(response.status_code, 200)
        entry = next(item for item in response.json()['waterbodies'] if item['id'] == self.body.pk)
        self.assertEqual(entry['map']['x_max'], 100)
        self.assertIn(self.fish.pk, [item['fish_id'] for item in entry['fish']])
        self.assertIn('csrftoken', response.cookies)

    def test_create_spot_converts_images_and_saves_order(self):
        response = self.client.post(reverse('fishing_spots:create'), self.payload())
        self.assertEqual(response.status_code, 200, response.content)
        spot = FishingSpot.objects.get(pk=response.json()['id'])
        self.assertIsNotNone(spot.created_at)
        self.assertEqual(spot.depth_cm, 250)
        self.assertEqual(spot.categories.count(), 2)
        self.assertEqual(list(spot.fish.values_list('pk', flat=True)), [self.fish.pk])
        self.assertEqual(list(spot.screenshots.values_list('position', flat=True)), [1, 2, 3, 4])
        for image in spot.screenshots.all():
            with Image.open(image.image.path) as saved:
                self.assertEqual(saved.format, 'WEBP')

    def test_invalid_coordinates_rejected_without_partial_writes(self):
        payload = self.payload()
        payload['coordinates'] = '200:44'
        response = self.client.post(reverse('fishing_spots:create'), payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FishingSpot.objects.count(), 0)
        self.assertEqual(FishingSpotScreenshot.objects.count(), 0)

    def test_mixed_fish_cannot_combine_with_specific_fish(self):
        payload = self.payload()
        payload['is_mixed_fish'] = 'true'
        response = self.client.post(reverse('fishing_spots:create'), payload)
        self.assertEqual(response.status_code, 400)

    def test_mixed_fish_without_specific_fish_is_valid(self):
        payload = self.payload()
        payload['is_mixed_fish'] = 'true'
        payload['fish_ids'] = '[]'
        response = self.client.post(reverse('fishing_spots:create'), payload)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(FishingSpot.objects.get(pk=response.json()['id']).is_mixed_fish)

    def test_reject_three_categories(self):
        payload = self.payload()
        payload['categories'] = json.dumps(['farm', 'trophy', 'task'])
        response = self.client.post(reverse('fishing_spots:create'), payload)
        self.assertEqual(response.status_code, 400)

    def test_reject_less_than_four_screenshots(self):
        payload = self.payload()
        payload['screenshots'] = [screenshot(i) for i in range(3)]
        response = self.client.post(reverse('fishing_spots:create'), payload)
        self.assertEqual(response.status_code, 400)

class SpotListTests(TestCase):
    def test_empty_page_and_navigation(self):
        response = self.client.get(reverse('fishing_spots:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Места ловли в Russian Fishing 4')
        self.assertContains(response, 'Места ловли по выбранным фильтрам не найдены.')
        self.assertContains(response, 'spot-filter-waterbody')

    def test_filters_and_pagination(self):
        body = Waterbody.objects.get(pk=1)
        other = Waterbody.objects.exclude(pk=body.pk).first()
        fish = Fish.objects.get(pk=105)
        another = Fish.objects.exclude(pk=fish.pk).first()
        first = FishingSpot.objects.create(waterbody=body, x=64, y=94, comment='Описание места')
        first.fish.add(fish)
        FishingSpotCategory.objects.create(fishing_spot=first, category='farm')
        FishingSpotCategory.objects.create(fishing_spot=first, category='trophy')
        for index in range(21):
            FishingSpot.objects.create(waterbody=other, x=index, y=10)
        response = self.client.get(reverse('fishing_spots:list'))
        self.assertEqual(len(response.context['page_obj']), 20)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 2)
        response = self.client.get(reverse('fishing_spots:list'), {'waterbody': body.pk, 'fish': fish.pk})
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertContains(response, fish.name)
        self.assertNotContains(response, 'Описание места')
        self.assertContains(response, 'Фарм')
        self.assertContains(response, 'Трофей')
        self.assertContains(response, 'spot-list-date')
        response = self.client.get(reverse('fishing_spots:list'), {'waterbody': body.pk, 'fish': another.pk})
        self.assertEqual(response.context['selected_fish'], '')

    def test_maps_dropdown_is_available_on_spot_list(self):
        response = self.client.get(reverse('fishing_spots:list'))
        self.assertContains(response, 'map-dropdown')
        body = Waterbody.objects.filter(is_active=True).order_by('sort_order', 'name', 'id').first()
        self.assertIsNotNone(body)
        self.assertContains(response, reverse('waterbodies:detail', args=[body.slug]))

    def test_mixed_fish_is_displayed_without_specific_species(self):
        body = Waterbody.objects.get(pk=1)
        FishingSpot.objects.create(waterbody=body, x=64, y=94, is_mixed_fish=True)
        response = self.client.get(reverse('fishing_spots:list'))
        self.assertContains(response, 'Разнорыбица')


class SpotDetailTests(TestCase):
    def test_spot_detail_contains_preview_without_wizard_steps(self):
        body = Waterbody.objects.get(pk=1)
        spot = FishingSpot.objects.create(
            waterbody=body, x=64, y=94, clip=18, depth_cm=250,
            retrieve_speed=35, comment='Точка у берега',
        )
        FishingSpotCategory.objects.create(fishing_spot=spot, category='farm')
        response = self.client.get(reverse('fishing_spots:detail', args=[spot.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Клипса')
        self.assertContains(response, '250 см')
        self.assertContains(response, 'Точка у берега')
        self.assertContains(response, 'Фарм')
        self.assertNotContains(response, 'spot-progress')

    def test_detail_hides_empty_optional_fields_and_moves_categories_to_header(self):
        body = Waterbody.objects.get(pk=1)
        spot = FishingSpot.objects.create(
            waterbody=body, x=64, y=94, is_mixed_fish=True,
            comment='   ',
        )
        FishingSpotCategory.objects.create(fishing_spot=spot, category='farm')
        FishingSpotCategory.objects.create(fishing_spot=spot, category='trophy')
        response = self.client.get(reverse('fishing_spots:detail', args=[spot.pk]))
        self.assertContains(response, 'data-spot-categories="Фарм, Трофей"')
        self.assertNotContains(response, '<dt class="col-sm-4 mb-2">Категория</dt>')
        for label in ('Клипса', 'Глубина', 'Скорость проводки', 'Комментарий'):
            self.assertNotContains(response, f'>{label}</dt>')
        self.assertContains(response, 'Разнорыбица')

    def test_detail_missing_spot_returns_404(self):
        response = self.client.get(reverse('fishing_spots:detail', args=[99999999]))
        self.assertEqual(response.status_code, 404)

    def test_add_button_and_detail_modal_on_list(self):
        response = self.client.get(reverse('fishing_spots:list'))
        self.assertContains(response, 'Добавить')
        self.assertContains(response, 'spot-detail-modal')

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import translation
from django.urls import reverse
from tempfile import TemporaryDirectory

from fish.models import Fish, WaterbodyFish

from .models import Waterbody, WaterbodyMap


class WaterbodyPagesTests(TestCase):
    def test_active_waterbody_has_detail_page_without_map(self):
        obj = Waterbody.objects.get(pk=1)
        response = self.client.get(reverse("waterbodies:detail", args=[obj.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, obj.name)
        self.assertContains(response, f"{obj.level} ур.")
        self.assertContains(response, "Карта этого водоёма пока не загружена")

    def test_inactive_waterbody_is_not_public(self):
        obj = Waterbody.objects.get(pk=1)
        obj.is_active = False
        obj.save()
        response = self.client.get(reverse("waterbodies:detail", args=[obj.slug]))
        self.assertEqual(response.status_code, 404)

    def test_home_cards_link_to_detail(self):
        obj = Waterbody.objects.get(pk=1)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, reverse("waterbodies:detail", args=[obj.slug]))

    def test_map_page_contains_image_viewer(self):
        with TemporaryDirectory() as directory:
            with override_settings(MEDIA_ROOT=directory):
                obj = Waterbody.objects.get(pk=4)
                map_obj = WaterbodyMap(waterbody=obj)
                map_obj.image.save("test.png", ContentFile(b"test image bytes"), save=True)
                response = self.client.get(reverse("waterbodies:detail", args=[obj.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="waterbody-map"')
                self.assertContains(response, "waterbody-map.js")
                self.assertContains(response, "Для отображения игровых координат настройте привязку карты")
                self.assertNotContains(response, "Перемещение карты отключено")

    def test_one_map_per_waterbody(self):
        field = WaterbodyMap._meta.get_field("waterbody")
        self.assertTrue(field.one_to_one)

    def test_detail_lists_only_active_fishes_of_selected_waterbody(self):
        waterbody = Waterbody.objects.get(pk=1)
        other = Waterbody.objects.get(pk=2)
        common = Fish.objects.create(name="А-тестовая рыба", trophy_weight=1000)
        rare = Fish.objects.create(name="Б-тестовая рыба", trophy_weight=2000, rarity=2)
        inactive = Fish.objects.create(name="В-неактивная рыба", trophy_weight=3000, is_active=False)
        elsewhere = Fish.objects.create(name="Г-другой водоём", trophy_weight=4000)
        for fish in (common, rare, inactive):
            WaterbodyFish.objects.create(waterbody=waterbody, fish=fish)
        WaterbodyFish.objects.create(waterbody=other, fish=elsewhere)

        response = self.client.get(reverse("waterbodies:detail", args=[waterbody.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["fishes"], [common, rare])
        self.assertContains(response, "Виды рыб")
        self.assertContains(response, "Видов: 2")
        self.assertContains(response, "fish-weights.js")
        self.assertNotContains(response, inactive.name)
        self.assertNotContains(response, elsewhere.name)

    def test_detail_renders_map_and_fishes_in_separate_tabs(self):
        waterbody = Waterbody.objects.get(pk=1)
        response = self.client.get(reverse("waterbodies:detail", args=[waterbody.slug]))
        self.assertContains(response, 'data-bs-target="#waterbody-map-pane"')
        self.assertContains(response, 'data-bs-target="#waterbody-fishes-pane"')
        self.assertContains(response, 'id="waterbody-map-pane"')
        self.assertContains(response, 'id="waterbody-fishes-pane"')
        self.assertContains(response, "Карта водоёма")
        self.assertContains(response, "Обитатели водоёма")

    def test_detail_with_no_fishes_shows_empty_message(self):
        waterbody = Waterbody.objects.get(pk=1)
        WaterbodyFish.objects.filter(waterbody=waterbody).delete()
        response = self.client.get(reverse("waterbodies:detail", args=[waterbody.slug]))
        self.assertContains(response, "Для этого водоёма виды рыб пока не указаны")

    def test_calibrated_map_includes_compass_bounds(self):
        with TemporaryDirectory() as directory:
            with override_settings(MEDIA_ROOT=directory):
                waterbody = Waterbody.objects.get(pk=1)
                game_map = WaterbodyMap.objects.create(
                    waterbody=waterbody, game_x_min=30, game_x_max=112,
                    game_y_min=33, game_y_max=115,
                )
                game_map.image.save("map.png", ContentFile(b"image"), save=True)
                response = self.client.get(reverse("waterbodies:detail", args=[waterbody.slug]))
                self.assertContains(response, 'data-game-x-min="30.0"')
                self.assertContains(response, 'data-game-x-max="112.0"')
                self.assertContains(response, 'data-game-y-min="33.0"')
                self.assertContains(response, 'data-game-y-max="115.0"')
                self.assertContains(response, "игровые координаты X:Y")

    def test_calibration_attributes_use_decimal_points_in_russian_locale(self):
        with TemporaryDirectory() as directory:
            with override_settings(MEDIA_ROOT=directory):
                waterbody = Waterbody.objects.get(pk=1)
                game_map = WaterbodyMap.objects.create(
                    waterbody=waterbody, game_x_min=38.5, game_x_max=162,
                    game_y_min=38, game_y_max=162,
                )
                game_map.image.save("map.png", ContentFile(b"image"), save=True)
                with translation.override("ru"):
                    response = self.client.get(reverse("waterbodies:detail", args=[waterbody.slug]))
                self.assertContains(response, 'data-game-x-min="38.5"')
                self.assertContains(response, 'data-game-x-max="162.0"')
                self.assertNotContains(response, 'data-image-left=')
                self.assertNotContains(response, 'data-image-right=')
                self.assertNotContains(response, 'data-image-top=')
                self.assertNotContains(response, 'data-image-bottom=')
                self.assertNotContains(response, 'data-game-x-min="38,5"')

    def test_partial_calibration_is_not_used(self):
        waterbody = Waterbody.objects.get(pk=1)
        game_map = WaterbodyMap(waterbody=waterbody, game_x_min=30)
        self.assertFalse(game_map.has_game_coordinates)

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from tempfile import TemporaryDirectory

from .models import Waterbody, WaterbodyMap


class WaterbodyPagesTests(TestCase):
    def test_active_waterbody_has_detail_page_without_map(self):
        obj = Waterbody.objects.get(pk=1)
        response = self.client.get(reverse("waterbodies:detail", args=[obj.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, obj.name)
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

    def test_one_map_per_waterbody(self):
        field = WaterbodyMap._meta.get_field("waterbody")
        self.assertTrue(field.one_to_one)

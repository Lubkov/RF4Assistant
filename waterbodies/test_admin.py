from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from fish.admin import FishAdmin
from fish.models import Fish, WaterbodyFish
from .admin import WaterbodyAdmin, WaterbodyFishInline
from .models import Waterbody


class AdminConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="admin-test", email="admin@example.test", password="test-password-123"
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_models_registered_and_inline_uses_fish_autocomplete(self):
        self.assertIsInstance(admin.site._registry[Waterbody], WaterbodyAdmin)
        self.assertIsInstance(admin.site._registry[Fish], FishAdmin)
        inline = WaterbodyAdmin.inlines[0]
        self.assertIs(inline, WaterbodyFishInline)
        self.assertEqual(inline.autocomplete_fields, ("fish",))
        self.assertIn("name", FishAdmin.search_fields)

    def test_waterbody_changelist_and_change_form(self):
        self.assertEqual(self.client.get(reverse("admin:waterbodies_waterbody_changelist")).status_code, 200)
        response = self.client.get(reverse("admin:waterbodies_waterbody_change", args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "оз. Комариное")
        self.assertContains(response, "waterbody_fish")

    def test_fish_changelist_and_change_form(self):
        self.assertEqual(self.client.get(reverse("admin:fish_fish_changelist")).status_code, 200)
        response = self.client.get(reverse("admin:fish_fish_change", args=[105]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Лещ")

    def test_image_preview_without_image(self):
        obj = Waterbody.objects.get(pk=1)
        self.assertEqual(admin.site._registry[Waterbody].image_preview(obj), "Изображение не загружено")

    def test_inline_relation_is_saved_and_unique(self):
        self.assertEqual(WaterbodyFish.objects.count(), 0)
        waterbody = Waterbody.objects.get(pk=1)
        fish = Fish.objects.get(pk=105)
        WaterbodyFish.objects.create(waterbody=waterbody, fish=fish)
        self.assertEqual(waterbody.waterbody_fish.count(), 1)

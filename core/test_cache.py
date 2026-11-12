from django.test import TestCase, override_settings
from django.urls import reverse
from django.template import Context, Template


class CachePolicyTests(TestCase):
    def test_html_is_not_stored_in_development(self):
        with override_settings(DEBUG=True):
            response = self.client.get(reverse("core:home"))
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_html_requires_validation_in_production(self):
        with override_settings(DEBUG=False, STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }):
            response = self.client.get(reverse("core:home"))
        self.assertEqual(response["Cache-Control"], "no-cache, must-revalidate")

    def test_static_url_changes_with_content_in_development(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from django.contrib.staticfiles import finders
        from unittest.mock import patch

        with TemporaryDirectory() as directory:
            filename = Path(directory) / "sample.css"
            filename.write_text("a{}")
            with override_settings(DEBUG=True), patch.object(finders, "find", return_value=str(filename)):
                tag = Template("{% load versioned_static %}{% versioned_static 'sample.css' %}")
                first = tag.render(Context())
                filename.write_text("b{}")
                second = tag.render(Context())
        self.assertNotEqual(first, second)
        self.assertIn("?v=", first)

from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from .models import Waterbody, WaterbodyMap


class ImageLifecycleTests(TestCase):
    def test_new_uploads_have_different_uuid_names_and_old_file_is_cleaned(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            obj = Waterbody.objects.get(pk=1)
            obj.image.save("lake.webp", ContentFile(b"image 1"))
            old_name = obj.image.name
            self.assertRegex(old_name, r"^waterbodies/[0-9a-f]{32}\.webp$")
            with self.captureOnCommitCallbacks(execute=True):
                obj.image.save("lake.webp", ContentFile(b"image 2"))
            new_name = obj.image.name
            self.assertNotEqual(old_name, new_name)
            self.assertFalse((Path(directory) / old_name).exists())
            self.assertTrue((Path(directory) / new_name).exists())

    def test_map_new_upload_uses_correct_folder(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            map_obj = WaterbodyMap(waterbody=Waterbody.objects.get(pk=1))
            map_obj.image.save("map.webp", ContentFile(b"image"))
            self.assertRegex(map_obj.image.name, r"^waterbodies/maps/[0-9a-f]{32}\.webp$")

    def test_map_replacement_deletes_old_file_after_commit(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            map_obj = WaterbodyMap(waterbody=Waterbody.objects.get(pk=1))
            map_obj.image.save("old.webp", ContentFile(b"old"))
            old_name = map_obj.image.name
            with self.captureOnCommitCallbacks(execute=True):
                map_obj.image.save("new.webp", ContentFile(b"new"))
            self.assertFalse((Path(directory) / old_name).exists())
            self.assertTrue((Path(directory) / map_obj.image.name).exists())

    def test_deletion_cleans_image_after_commit(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            obj = WaterbodyMap(waterbody=Waterbody.objects.get(pk=1))
            obj.image.save("map.webp", ContentFile(b"image"))
            old_name = obj.image.name
            with self.captureOnCommitCallbacks(execute=True):
                obj.delete()
            self.assertFalse((Path(directory) / old_name).exists())

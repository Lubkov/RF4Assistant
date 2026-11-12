"""Immutable, unique filenames for newly uploaded waterbody images."""
from pathlib import Path
from uuid import uuid4


def _image_path(directory, filename):
    # Preserve the real extension: renaming PNG bytes to .webp does NOT convert.
    # Prepared WebP images naturally get UUID.webp filenames.
    extension = Path(filename).suffix.lower() or ".webp"
    return f"{directory}/{uuid4().hex}{extension}"


def waterbody_image_path(instance, filename):
    return _image_path("waterbodies", filename)


def waterbody_map_path(instance, filename):
    return _image_path("waterbodies/maps", filename)

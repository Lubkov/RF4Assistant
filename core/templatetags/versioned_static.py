"""Use built-in manifest URLs in production; content hashes in development."""
import hashlib
from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def versioned_static(path):
    url = static(path)
    if settings.DEBUG:
        source = finders.find(path)
        if source and Path(source).is_file():
            digest = hashlib.sha256(Path(source).read_bytes()).hexdigest()[:12]
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}v={digest}"
    return url

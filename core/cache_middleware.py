"""Prevent browsers from reusing outdated HTML (including HTMX fragments)."""
from django.conf import settings


class HtmlCacheControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Do not overwrite policies for static/media, downloads, redirects etc.
        if response.get("Content-Type", "").lower().startswith("text/html"):
            response["Cache-Control"] = (
                "no-store" if settings.DEBUG else "no-cache, must-revalidate"
            )
        return response

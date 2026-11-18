"""Shared template data for the global navigation."""

from waterbodies.models import Waterbody


def navigation(request):
    return {
        "navigation_waterbodies": Waterbody.objects.filter(is_active=True).order_by(
            "sort_order", "name", "id"
        )
    }

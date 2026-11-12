from django.apps import AppConfig


class WaterbodiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "waterbodies"
    verbose_name = "Водоёмы"

    def ready(self):
        # Register cleanup signals exactly once per process.
        from . import file_cleanup  # noqa: F401

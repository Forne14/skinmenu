# /media_derivatives/apps.py
from django.apps import AppConfig


class MediaDerivativesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "media_derivatives"
    verbose_name = "Media Derivatives"

    def ready(self) -> None:
        # Register signal handlers
        from . import signals  # noqa: F401

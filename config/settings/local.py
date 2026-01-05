import os


def _csv_env(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    # split, strip, drop empties
    return [h.strip() for h in raw.split(",") if h.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-key")


ALLOWED_HOSTS = _csv_env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = _csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")

WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", "https://skin-menu.co.uk")

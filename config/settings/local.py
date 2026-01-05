import os


def _csv_env(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [h.strip() for h in raw.split(",") if h.strip()]


# Required in prod (deploy.sh sources /etc/skinmenu/skinmenu.env)
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# Strongly recommended to set in prod env:
# DJANGO_ALLOWED_HOSTS="skin-menu.co.uk,www.skin-menu.co.uk"
ALLOWED_HOSTS = _csv_env("DJANGO_ALLOWED_HOSTS")

# Recommended to set in prod env:
# DJANGO_CSRF_TRUSTED_ORIGINS="https://skin-menu.co.uk,https://www.skin-menu.co.uk"
CSRF_TRUSTED_ORIGINS = _csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")

# Wagtail admin base URL for notification emails
WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", "https://www.skin-menu.co.uk")

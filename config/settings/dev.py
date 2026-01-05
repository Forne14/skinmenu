from .base import *

DEBUG = True

# Dev-only key (override in config/settings/local.py if you want)
SECRET_KEY = "dev-only-not-for-production"

# For local dev convenience
ALLOWED_HOSTS = ["www.skin-menu.co.uk", "skin-menu.co.uk", "localhost", "127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# If you're testing HTTPS locally via a proxy, set these in local.py/env instead
CSRF_TRUSTED_ORIGINS = []

try:
    from .local import *
except ImportError:
    pass

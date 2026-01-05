from .base import *

DEBUG = True

# Dev-only key (override in config/settings/local.py if you want)
SECRET_KEY = "dev-only-not-for-production"

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Make debugging friendlier behind proxies/containers sometimes
CSRF_TRUSTED_ORIGINS = []

try:
    from .local import *
except ImportError:
    pass

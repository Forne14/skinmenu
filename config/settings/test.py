from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Keep tests hermetic; no network cache/Redis dependency.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "skinmenu-tests",
    }
}

# Fast and deterministic email behavior for tests.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Avoid hashed static manifest requirement in tests.
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Explicitly disable secure-cookie/redirect requirements in test client context.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Keep admin URL generation deterministic in tests.
WAGTAILADMIN_BASE_URL = "http://testserver"
LOGIN_URL = "/admin/login/"

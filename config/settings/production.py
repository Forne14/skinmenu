from .base import *

DEBUG = False

# Serve hashed static file names + cache-busting in production
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Trust reverse proxy header (nginx should set X-Forwarded-Proto)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies over HTTPS only
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Security headers
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days to start
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # only True when you're ready to preload

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# If nginx already does HTTP->HTTPS redirect, it's okay to keep False.
# If you want belt-and-suspenders, change to True AFTER confirming proxy header behavior.
SECURE_SSL_REDIRECT = False

try:
    from .local import *
except ImportError:
    pass

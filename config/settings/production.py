from .base import *

DEBUG = False

# Serve hashed static file names + cache-busting in production
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# If you're behind nginx (you are), tell Django to trust X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies should be secure in HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Recommended security headers
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days to start
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # set True only when you're sure

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Django 5+ can use this to enforce HTTPS redirects (nginx can also do it)
SECURE_SSL_REDIRECT = False  # nginx/certbot already handles redirect

try:
    from .local import *
except ImportError:
    pass

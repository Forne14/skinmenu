"""
Base settings shared by dev + production.
"""

from pathlib import Path
import os

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent


# --------------------------------------------------------------------
# Core Django
# --------------------------------------------------------------------
INSTALLED_APPS = [
    "pages",
    "search",
    "media_derivatives",
    "django_rq",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "wagtail.contrib.settings",
    "site_settings",
    "colorfield",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --------------------------------------------------------------------
# Database
# --------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# --------------------------------------------------------------------
# Password validation
# --------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------
# Static + Media
# --------------------------------------------------------------------
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# IMPORTANT:
# - STATICFILES_DIRS points at *source* static files in the repo.
# - STATIC_ROOT is where collectstatic writes its output (should be separate).
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# source static (repo)
STATICFILES_DIRS = [
    PROJECT_DIR / "static",
]

# collected static output (keep separate to avoid clobbering source files)
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
NEWSLETTER_CSV_PATH = Path(
    os.environ.get("NEWSLETTER_CSV_PATH", str(BASE_DIR / "var" / "newsletter_signups.csv"))
)


# Storage backends (production overrides staticfiles backend to ManifestStaticFilesStorage)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# --------------------------------------------------------------------
# Wagtail
# --------------------------------------------------------------------
WAGTAIL_SITE_NAME = "Skinmenu"

WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

# Use HTTPS by default; can be overridden via env in local.py
WAGTAILADMIN_BASE_URL = "https://www.skin-menu.co.uk"

WAGTAILDOCS_EXTENSIONS = [
    "csv", "docx", "key", "odt", "pdf", "pptx", "rtf", "txt", "xlsx", "zip",
    "mp4", "mov", "webm", "png", "jpg", "jpeg", "gif", "svg", "bmp", "tiff",
    "avi", "wmv",
]


WAGTAILDOCS_CONTENT_TYPES = {
    # keep any existing entries
    "pdf": "application/pdf",
    "txt": "text/plain",
    "mp4": "video/mp4",
}

# settings.py

WAGTAILDOCS_INLINE_CONTENT_TYPES = [
    "application/pdf",
    "text/plain",
    "video/mp4",
]

WAGTAILDOCS_SERVE_METHOD = "direct"



# --------------------------------------------------------------------
# Safety defaults (overridden in dev/production/local)
# --------------------------------------------------------------------
DEBUG = False
SECRET_KEY = "change-me"
ALLOWED_HOSTS: list[str] = []

# Wagtail/Django forms can get large
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000


REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

RQ_QUEUES = {
    "default": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 60 * 20,  # 20 minutes
    }
}

# --------------------------------------------------------------------
# Cache (shared)
# --------------------------------------------------------------------
# Uses the same Redis as RQ by default. If you want separation later,
# set REDIS_CACHE_URL separately.
REDIS_CACHE_URL = os.environ.get("REDIS_CACHE_URL", REDIS_URL)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Optional: compress cached values (good for JSON-ish dict payloads)
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "TIMEOUT": 300,  # default; individual cache.set overrides this
    }
}

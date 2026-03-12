"""
Base settings shared by dev + production.
"""

from pathlib import Path
import os
from urllib.parse import urlparse, unquote

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent


# --------------------------------------------------------------------
# Core Django
# --------------------------------------------------------------------
INSTALLED_APPS = [
    "integrations",
    "catalog",
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
def _database_from_env() -> dict[str, str | int]:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }

    parsed = urlparse(url)
    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": (parsed.path or "/")[1:] or "postgres",
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "127.0.0.1",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
        }

    raise RuntimeError("Unsupported DATABASE_URL scheme. Use sqlite (default) or postgres/postgresql.")


DATABASES = {"default": _database_from_env()}


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

# --------------------------------------------------------------------
# Integration adapters (safe defaults)
# --------------------------------------------------------------------
LEAD_SYNC_ENABLED = os.environ.get("LEAD_SYNC_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
LEAD_SYNC_BACKEND = os.environ.get("LEAD_SYNC_BACKEND", "noop")
LEAD_SYNC_WEBHOOK_URL = os.environ.get("LEAD_SYNC_WEBHOOK_URL", "")
LEAD_SYNC_TIMEOUT_SECONDS = int(os.environ.get("LEAD_SYNC_TIMEOUT_SECONDS", "8"))
LEAD_SYNC_QUEUE = os.environ.get("LEAD_SYNC_QUEUE", "default")
LEAD_SYNC_MAX_ATTEMPTS = int(os.environ.get("LEAD_SYNC_MAX_ATTEMPTS", "3"))
LEAD_SYNC_RETRY_DELAYS = os.environ.get("LEAD_SYNC_RETRY_DELAYS", "30,120,300")

BOOKING_BASE_URL = os.environ.get("BOOKING_BASE_URL", "").strip()

# Optional S3-compatible media storage (disabled by default)
USE_S3_STORAGE = os.environ.get("USE_S3_STORAGE", "0").lower() in {"1", "true", "yes", "on"}
if USE_S3_STORAGE:
    if "storages" not in INSTALLED_APPS:
        INSTALLED_APPS.append("storages")
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ.get("AWS_STORAGE_BUCKET_NAME", "").strip(),
            "access_key": os.environ.get("AWS_ACCESS_KEY_ID", "").strip(),
            "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip(),
            "region_name": os.environ.get("AWS_S3_REGION_NAME", "").strip() or None,
            "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL", "").strip() or None,
            "default_acl": None,
            "file_overwrite": False,
        },
    }
    custom_domain = os.environ.get("AWS_S3_CUSTOM_DOMAIN", "").strip()
    if custom_domain:
        MEDIA_URL = f"https://{custom_domain}/"

"""Base settings shared across environments.

Loads configuration from environment variables (.env in development,
real env vars on the server in production). NEVER hardcode secrets here.
"""
from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    EMAIL_USE_TLS=(bool, True),
    SECURE_SSL_REDIRECT=(bool, False),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("SECRET_KEY", default="insecure-development-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",

    "rest_framework",
    "tinymce",

    "apps.core",
    "apps.news",
    "apps.pages",
    "apps.accounts",
    "apps.gallery",
    "apps.documents",
]

def _admin_navigation(request):
    """Lazy wrapper so Unfold builds the sidebar at request time.

    Deferring the import keeps settings free of app-registry access at load.
    """
    from apps.core.admin_nav import build_navigation

    return build_navigation(request)


UNFOLD = {
    "SITE_TITLE": "Адмінпанель ФПУ",
    "SITE_HEADER": "Федерація Профспілок України",
    "SITE_SYMBOL": "shield_person",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "font": {
            "subtle-light": "107 114 128",
            "subtle-dark": "156 163 175",
            "default-light": "75 85 99",
            "default-dark": "209 213 219",
            "important-light": "17 24 39",
            "important-dark": "243 244 246",
        },
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": _admin_navigation,
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_chrome",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

# TCP keepalive prevents PostgreSQL from dropping SSL connections
# during long bulk operations (loaddata / load_fixtures with large fixtures).
if DATABASES["default"].get("ENGINE", "").endswith("psycopg2"):
    DATABASES["default"].setdefault("OPTIONS", {}).update({
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    })

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("uk", "Українська"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# ── Cache ──────────────────────────────────────────────────────────────────────
# REDIS_URL береться з env (опційно, для rate-limiting контактної форми).
# Без Redis падаємо на LocMemCache (dev/тести/перший деплой без Redis).
_redis_url = env("REDIS_URL", default="")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="webmaster@localhost")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ── TinyMCE (admin WYSIWYG — Joomla-like) ─────────────────────────────────────
TINYMCE_DEFAULT_CONFIG = {
    "height": 520,
    "width": "100%",
    "skin": "oxide",
    "content_css": "default",
    "menubar": "file edit view insert format tools table help",
    "plugins": (
        "advlist autolink lists link image charmap preview anchor searchreplace "
        "visualblocks code fullscreen insertdatetime media table help wordcount "
        "directionality quickbars autosave"
    ),
    "toolbar": (
        "undo redo | blocks fontfamily fontsize | "
        "bold italic underline strikethrough subscript superscript | "
        "forecolor backcolor removeformat | "
        "alignleft aligncenter alignright alignjustify | "
        "bullist numlist outdent indent | "
        "link unlink anchor image media table hr | "
        "code fullscreen"
    ),
    "block_formats": (
        "Абзац=p; Заголовок 2=h2; Заголовок 3=h3; Заголовок 4=h4; "
        "Цитата=blockquote; Код=pre"
    ),
    "font_family_formats": (
        "Open Sans=Open Sans,sans-serif; Arial=arial,helvetica,sans-serif; "
        "Times New Roman=times new roman,times,serif; Courier New=courier new,courier,monospace"
    ),
    "fontsize_formats": "8pt 10pt 12pt 14pt 16pt 18pt 24pt 36pt",
    "image_advtab": True,
    "image_caption": True,
    "paste_data_images": True,
    "relative_urls": False,
    "convert_urls": False,
    "entity_encoding": "raw",
    "browser_spellcheck": True,
    "promotion": False,
    "branding": False,
    "resize": True,
    "quickbars_selection_toolbar": (
        "bold italic underline | blocks | quicklink blockquote"
    ),
    "images_upload_handler": "fpsuTinyMceUploadHandler",
    "setup": "fpsuTinyMceSetup",
    "content_style": (
        "body { font-family: 'Open Sans', Arial, sans-serif; "
        "font-size: 14px; line-height: 1.6; color: #1a2238; "
        "background: #fff; }"
        "img { max-width: 100%; height: auto; }"
    ),
}

TINYMCE_EXTRA_MEDIA = {
    "js": ["admin/js/tinymce_body.js"],
    "css": {"all": ["admin/css/tinymce_unfold.css"]},
}

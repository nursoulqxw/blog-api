#Python modules
import os
from decouple import config

#Django modules

#Django Resr Framework modules

#Project modules
from django.utils.translation import gettext_lazy as _
from celery.schedules import crontab

from settings.conf import (
    BLOG_SECRET_KEY,
    BLOG_ALLOWED_HOSTS,
    BLOG_REDIS_URL,
    SIMPLE_JWT_SETTINGS,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_CELERY_DB,
    REDIS_CHANNEL_DB,
    BLOG_CELERY_BROKER_URL,
    BLOG_CELERY_RESULT_BACKEND,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = BLOG_SECRET_KEY
ALLOWED_HOSTS = BLOG_ALLOWED_HOSTS

# modeltranslation must appear before django.contrib.admin
DJANGO_AND_THIRD_PARTY_APPS = [
    "modeltranslation",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",

    "channels",
    "apps.core",
    "apps.users",
    "apps.blog",
    "apps.notifications",
]

PROJECT_APPS = []

INSTALLED_APPS = DJANGO_AND_THIRD_PARTY_APPS + PROJECT_APPS #concationation 

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # LanguageTimezoneMiddleware comes before LocaleMiddleware so the
    # language is activated before Django's locale processing.
    "apps.core.middleware.LanguageTimezoneMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "settings.wsgi.application"
ASGI_APPLICATION = "settings.asgi.application"

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "register": "5/min",
        "token": "10/min",
        "post_create": "20/min",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Blog API",
    "DESCRIPTION": "Blog API documentation",
    "VERSION": "1.0.0",
}

SIMPLE_JWT = SIMPLE_JWT_SETTINGS

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "WARNING",
            "formatter": "verbose",
            "filename": "logs/app.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
        },
    },
    "loggers": {
        "users": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "blog": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "data", "db.sqlite3"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": BLOG_REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "blogapi",
    }
}

# Celery
_celery_redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
CELERY_BROKER_URL = BLOG_CELERY_BROKER_URL
CELERY_RESULT_BACKEND = BLOG_CELERY_RESULT_BACKEND
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {
    "cleanup-tokens": {
        "task": "users.tasks.cleanup_expired_tokens",
        "schedule": 30 * 60,  # every 30 min
    },
    "daily-report": {
        "task": "reports.tasks.generate_daily_report",
        "schedule": crontab(hour=0, minute=0),  # midnight
    },
    "weekly-digest": {
        "task": "notifications.tasks.send_weekly_digest",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday 09:00
    },
}

# Email — overridden per environment
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = "Blog API <noreply@blogapi.local>"

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

ENGLISH_LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", _("English")),
    ("kk", _("Kazakh")),
    ("ru", _("Russian")),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

# Static | Media
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
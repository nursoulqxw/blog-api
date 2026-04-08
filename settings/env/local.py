import os

from settings.base import *  # noqa: F401, F403


DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# Print emails to console during local development instead of sending them
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Add debug_requests handler — only active when DEBUG=True via RequireDebugTrue filter
LOGGING["handlers"]["debug_requests"] = {  # noqa: F405
    "class": "logging.handlers.RotatingFileHandler",
    "level": "DEBUG",
    "formatter": "verbose",
    "filename": os.path.join(BASE_DIR, "logs", "debug_requests.log"),  # noqa: F405
    "maxBytes": 5 * 1024 * 1024,
    "backupCount": 3,
    "filters": ["require_debug_true"],
}

LOGGING["loggers"]["django.request"]["handlers"].append("debug_requests")  # noqa: F405
from settings.base import *

import os

LOGGING["filters"] = {
    "require_debug_true": {
        "()": "django.utils.log.RequireDebugTrue",
    },
}

LOGGING["handlers"]["debug_requests"] = {
    "class": "logging.handlers.RotatingFileHandler",
    "level": "DEBUG",
    "formatter": "verbose",
    "filename": os.path.join(BASE_DIR, "logs", "debug_requests.log"),
    "maxBytes": 5 * 1024 * 1024,
    "backupCount": 3,
    "filters": ["require_debug_true"],
}

LOGGING["loggers"]["django.request"]["handlers"].append("debug_requests")



DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


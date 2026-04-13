import os
from datetime import timedelta

from decouple import config, Csv

SECRET_KEY = config("BLOG_SECRET_KEY", "any-default-secret-key", cast=str) # adv-django
ENV_ID = config("PROJECT_ENV_ID", default = "local", cast=str) # adv-django
ALLOWED_ENV_IDS = ("local", "prod") # avd-django vid tutor

# Core
BLOG_SECRET_KEY: str = config("BLOG_SECRET_KEY", default="dev-secret-key-change-in-prod") # ai
BLOG_DEBUG: bool = config("BLOG_DEBUG", default=False, cast=bool)
BLOG_ALLOWED_HOSTS: list = config("BLOG_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# Database (used in prod.py)
BLOG_DB_NAME: str = config("BLOG_DB_NAME", default="blog")
BLOG_DB_USER: str = config("BLOG_DB_USER", default="blog")
BLOG_DB_PASSWORD: str = config("BLOG_DB_PASSWORD", default="")
BLOG_DB_HOST: str = config("BLOG_DB_HOST", default="localhost")
BLOG_DB_PORT: str = config("BLOG_DB_PORT", default="5432")

# Redis
BLOG_REDIS_URL: str = config("BLOG_REDIS_URL", default="redis://127.0.0.1:6379/1")

# JWT
BLOG_ACCESS_TOKEN_LIFETIME_MINUTES: int = config(
    "BLOG_ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int
)
BLOG_REFRESH_TOKEN_LIFETIME_DAYS: int = config(
    "BLOG_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int
)

SIMPLE_JWT_SETTINGS: dict = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=BLOG_ACCESS_TOKEN_LIFETIME_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=BLOG_REFRESH_TOKEN_LIFETIME_DAYS),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Redis Configuration
REDIS_HOST = config("BLOG_REDIS_HOST", cast=str, default="localhost")
REDIS_PORT = config("BLOG_REDIS_PORT", cast=int, default=6379)
REDIS_CELERY_DB = config("BLOG_REDIS_CELERY_DB", cast=int, default=2)
REDIS_CACHE_DB = config("BLOG_REDIS_CACHE_DB", cast=int, default=1)
REDIS_CHANNEL_DB = config("BLOG_REDIS_CHANNEL_DB", cast=int, default=0)

#CELERY
BLOG_CELERY_BROKER_URL: str = config("BLOG_CELERY_BROKER_URL", default="redis://127.0.0.1:6379/2")
BLOG_CELERY_RESULT_BACKEND: str = config("BLOG_CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/3")
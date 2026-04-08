from datetime import timedelta

from decouple import config, Csv


# Core
BLOG_SECRET_KEY: str = config("BLOG_SECRET_KEY", default="dev-secret-key-change-in-prod")
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
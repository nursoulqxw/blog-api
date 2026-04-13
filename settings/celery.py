import os
from decouple import config
from celery import Celery
from celery.schedules import crontab

_env_id = config("BLOG_ENV_ID", default="local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{_env_id}")

app = Celery("blog")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "publish-scheduled-posts": {
        "task": "apps.blog.tasks.publish_scheduled_posts",
        "schedule": 60,  # every 1 minute
    },
    "clear-expired-notifications": {
        "task": "apps.notifications.tasks.clear_expired_notifications",
        "schedule": crontab(hour=3, minute=0),  # daily at 03:00
    },
    "generate-daily-stats": {
        "task": "apps.blog.tasks.generate_daily_stats",
        "schedule": crontab(hour=0, minute=0),  # daily at 00:00
    },
}

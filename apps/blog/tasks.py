import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("blog")

# Retries are important for cache invalidation because Redis can be temporarily
# unavailable. If invalidation fails silently, users get stale data indefinitely.
# Retrying with backoff ensures the cache version is eventually bumped and users
# stop receiving stale post lists.

@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def invalidate_posts_cache():
    try:
        cache.incr("posts:list:version")
    except ValueError:
        cache.set("posts:list:version", 2, None)


# Retries are important here because publishing a post involves both a DB write
# and a Redis publish. If either fails temporarily, retrying ensures the post
# gets published and SSE subscribers are notified.
@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def publish_scheduled_posts():
    from apps.blog.models import Post
    from django.db import transaction
    import json
    from django_redis import get_redis_connection

    now = timezone.now()
    posts = Post.objects.filter(status=Post.Status.SCHEDULED, publish_at__lte=now)

    for post in posts:
        with transaction.atomic():
            post.status = Post.Status.PUBLISHED
            post.save()

            payload = json.dumps({
                "post_id": post.id,
                "title": post.title,
                "slug": post.slug,
                "author": {
                    "id": post.author.id,
                    "email": post.author.email,
                },
                "published_at": post.updated_at.isoformat(),
            })
            redis_conn = get_redis_connection("default")
            redis_conn.publish("posts:published", payload)

        logger.info("Auto-published scheduled post slug=%s", post.slug)

    invalidate_posts_cache.delay()


# Retries are important for stats logging because DB queries can fail due to
# temporary connection issues. Retrying ensures stats are always logged.
@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_daily_stats():
    from apps.blog.models import Post, Comment
    from django.contrib.auth import get_user_model

    User = get_user_model()
    since = timezone.now() - timezone.timedelta(hours=24)

    new_posts = Post.objects.filter(created_at__gte=since).count()
    new_comments = Comment.objects.filter(created_at__gte=since).count()
    new_users = User.objects.filter(date_joined__gte=since).count()

    logger.info(
        "Daily stats — new posts: %d, new comments: %d, new users: %d",
        new_posts, new_comments, new_users,
    )

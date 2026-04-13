import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("notifications")

# Retries are important for comment processing because both the database write
# (Notification.objects.create) and the Channels layer group_send go over the
# network. Either can fail transiently due to Redis restarts or connection
# spikes. Without retries, a failure silently drops the notification and the
# WebSocket event — the post author never knows someone commented. Exponential
# backoff prevents thundering-herd reconnection storms during an outage.

@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_new_comment(comment_id: int) -> str:
    from apps.blog.models import Comment
    from apps.notifications.models import Notification
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    comment = Comment.objects.select_related("post__author", "author").get(id=comment_id)
    post = comment.post
    post_author = post.author

    # Create notification only when someone else comments on the post.
    if comment.author != post_author:
        Notification.objects.create(recipient=post_author, comment=comment)

    # Broadcast to every WebSocket client currently viewing this post.
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"post_{post.slug}",
        {
            "type": "comment_created",
            "data": {
                "comment_id": comment.id,
                "author": {
                    "id": comment.author.id,
                    "email": comment.author.email,
                },
                "body": comment.body,
                "created_at": comment.created_at.isoformat(),
            },
        },
    )

    logger.info(
        "process_new_comment done comment_id=%s post_slug=%s",
        comment_id,
        post.slug,
    )
    return f"Processed comment {comment_id}"

# Retries are important here because a DB connection failure during cleanup
# would leave expired notifications in the database indefinitely.
@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def clear_expired_notifications():
    from apps.notifications.models import Notification

    cutoff = timezone.now() - timezone.timedelta(days=30)
    deleted, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Cleared %d expired notifications", deleted)
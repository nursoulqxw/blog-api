from rest_framework.serializers import (
    ModelSerializer,
    CharField,
)

from .models import Notification

class NotificationSerializer(ModelSerializer):
    comment_body = CharField(source="comment.body", read_only=True)
    post_slug = CharField(source="comment.post.slug", read_only=True)
    commenter = CharField(source="comment.author.username", read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'commenter', 'comment_body', 'post_slug', 'is_read', 'created_at']
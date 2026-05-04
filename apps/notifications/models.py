#Django modules
from django.db.models import (
    ForeignKey,
    BooleanField,
    DateTimeField,
    CASCADE,
    Model,
)

#Project modules
from apps.blog.models import Comment
from apps.users.models import User

# Create your models here.

class Notification(Model):
    recipient = ForeignKey(User, on_delete=CASCADE)
    comment = ForeignKey(Comment, on_delete=CASCADE)
    is_read = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient} -- comment {self.comment_id}"

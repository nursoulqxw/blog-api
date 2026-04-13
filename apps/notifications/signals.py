# Notification creation on comment is handled by the process_new_comment
# Celery task (apps/notifications/tasks.py), which is dispatched from the
# comments view after the Comment is saved.  There is nothing to do here.

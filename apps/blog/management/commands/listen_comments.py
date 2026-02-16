from django.core.management.base import BaseCommand
from django_redis import get_redis_connection


class Command(BaseCommand):
    help = "Listen to Redis pub/sub channel 'comments'"

    def handle(self, *args, **options):
        redis_conn = get_redis_connection("default")

        pubsub = redis_conn.pubsub()
        pubsub.subscribe("comments")

        self.stdout.write(self.style.SUCCESS("Listening on Redis channel: comments"))

        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = message["data"]

            try:
                text = data.decode("utf-8")
            except Exception:
                text = str(data)

            self.stdout.write(f"EVENT → {text}")
    
"""
Async Redis pub/sub listener for the 'comments' channel.

Why async?
----------
pub/sub listening is pure I/O waiting: the process sits idle until a
message arrives over the network.  A synchronous implementation would
block a thread the entire time, wasting OS resources.

Using asyncio + the async Redis client (redis.asyncio) means the event
loop can handle other coroutines (logging, signal handling, etc.) while
waiting for messages — with zero threads.

If this were written synchronously, the blocking ``for msg in
pubsub.listen()`` call would pin one thread forever.
"""
import asyncio
import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand


logger = logging.getLogger("blog")


class Command(BaseCommand):
    help = "Subscribe to Redis pub/sub channel 'comments' (async)"

    def handle(self, *args, **options) -> None:
        asyncio.run(self._listen())

    async def _listen(self) -> None:
        import redis.asyncio as aioredis

        redis_url: str = settings.CACHES["default"]["LOCATION"]
        redis: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=True)

        async with redis.pubsub() as pubsub:
            await pubsub.subscribe("comments")
            self.stdout.write(
                self.style.SUCCESS("Listening on Redis channel: comments")
            )
            logger.info("listen_comments started on channel 'comments'")

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                raw: str = message["data"]

                try:
                    event: dict = json.loads(raw)
                    self.stdout.write(
                        f"EVENT → post={event.get('post_slug')!r} "
                        f"author={event.get('author_id')} "
                        f"body={event.get('body')!r}"
                    )
                    logger.debug("Comment event received: %s", event)
                except json.JSONDecodeError:
                    self.stdout.write(f"EVENT (raw) → {raw}")
import json
import logging
from urllib.parse import urlencode

import redis.asyncio as aioredis
from django.conf import settings
from django.core.cache import cache
from django.db.models import QuerySet
from django.http import StreamingHttpResponse
from django.utils import timezone
from django_redis import get_redis_connection

from rest_framework import status
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from .models import Post, Comment
from .permissions import IsOwnerOrReadOnly
from .serializers import PostSerializer, CommentSerializer
from .tasks import invalidate_posts_cache
from .throttles import PostCreateUserThrottle
from apps.notifications.tasks import process_new_comment

logger = logging.getLogger("blog")

# ---------------------------------------------------------------------------
# SSE: why SSE and not WebSockets?
#
# SSE is a perfect fit for a "new post published" feed because the flow is
# strictly server → client (unidirectional).  The browser's built-in
# EventSource API handles reconnections automatically over a plain HTTP/1.1
# or HTTP/2 connection, with no extra handshake protocol needed.
#
# Choose WebSockets instead when you need full-duplex communication — e.g.
# collaborative editing, chat, or any scenario where the client must also
# push data back to the server over the same persistent connection.
# ---------------------------------------------------------------------------

_REDIS_PUBSUB_CHANNEL = "posts:published"


async def post_stream(request):
    """
    GET /api/posts/stream/

    Keeps the connection open and pushes an SSE event each time a post
    transitions to published status.  No authentication required.

    Event format::

        event: post_published
        data: {"post_id": 1, "title": "...", "slug": "...",
                "author": {"id": 1, "email": "..."},
                "published_at": "2026-04-11T10:00:00+00:00"}

    """

    async def event_generator():
        redis_url = settings.CACHES["default"]["LOCATION"]
        r = await aioredis.from_url(redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(_REDIS_PUBSUB_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"event: post_published\ndata: {data}\n\n"
        finally:
            await pubsub.unsubscribe(_REDIS_PUBSUB_CHANNEL)
            await r.aclose()

    response = StreamingHttpResponse(event_generator(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    # Tell Nginx not to buffer this response so events reach the client immediately.
    response["X-Accel-Buffering"] = "no"
    return response


def post_poll(request):
    """
    GET /api/posts/poll/?since=<iso8601-timestamp>

    HTTP Polling endpoint — returns all published posts created after `since`.
    If `since` is omitted, returns posts from the last 60 seconds.

    Clients call this repeatedly on an interval (e.g. every 5 s) to simulate
    real-time updates without a persistent connection.

    Response::

        {
            "timestamp": "2026-04-13T10:00:00+00:00",
            "posts": [{"post_id": 1, "title": "...", "slug": "...",
                        "author": {"id": 1, "email": "..."},
                        "published_at": "..."}]
        }
    """
    from datetime import datetime, timezone as dt_timezone

    since_param = request.GET.get("since")
    if since_param:
        try:
            since = datetime.fromisoformat(since_param)
            if since.tzinfo is None:
                since = since.replace(tzinfo=dt_timezone.utc)
        except ValueError:
            from rest_framework.response import Response as DRFResponse
            return DRFResponse({"detail": "Invalid `since` format. Use ISO 8601."}, status=400)
    else:
        since = timezone.now() - timezone.timedelta(seconds=60)

    from apps.blog.models import Post
    posts = Post.objects.filter(
        status=Post.Status.PUBLISHED,
        published_at__gt=since,
    ).select_related("author").order_by("published_at")

    data = {
        "timestamp": timezone.now().isoformat(),
        "posts": [
            {
                "post_id": p.id,
                "title": p.title,
                "slug": p.slug,
                "author": {"id": p.author.id, "email": p.author.email},
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
            for p in posts
        ],
    }
    from django.http import JsonResponse
    return JsonResponse(data)


class PostViewSet(ModelViewSet):
    serializer_class = PostSerializer
    lookup_field = "slug"
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_throttles(self):
        if self.action == "create":
            return [PostCreateUserThrottle()]
        return []

    def get_queryset(self) -> QuerySet:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return Post.objects.filter(status=Post.Status.PUBLISHED)
        return Post.objects.all()

    def _bump_posts_list_cache_version(self):
        try:
            cache.incr("posts:list:version")
        except ValueError:
            cache.set("posts:list:version", 2, None)

    @extend_schema(
        tags=["Posts"],
        summary="List posts",
        description="""
        Return a list of published blog posts.

        **Caching:**
        - response is cached for a short time
        - cache is invalidated when posts are created, updated, or deleted
        """,
        responses={
            HTTP_200_OK: PostSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "Posts list response",
                value=[
                    {
                        "title": "First post",
                        "slug": "first-post",
                        "status": "published",
                    }
                ],
                response_only=True,
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        version = cache.get("posts:list:version")
        if version is None:
            cache.set("posts:list:version", 1, None)
            version = 1

        # Language-aware cache key: Russian and English users get
        # independently cached responses so translated category names
        # and localised dates are served correctly.
        lang = getattr(request, "LANGUAGE_CODE", "en")
        params = request.query_params.dict()
        params_str = urlencode(sorted(params.items()))
        cache_key = f"posts:list:v{version}:{lang}:{params_str}"

        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Posts list cache hit key=%s", cache_key)
            return Response(cached)

        logger.debug("Posts list cache miss key=%s", cache_key)
        response = super().list(request, *args, **kwargs)

        if response.status_code == HTTP_200_OK:
            cache.set(cache_key, response.data, 60)

        return response

    @extend_schema(
        tags=["Posts"],
        summary="Create post",
        description="""
        Create a new blog post.

        **Authorization required:** Bearer token

        **Rate limit:**
        - limited per authenticated user
        """,
        request=PostSerializer,
        responses={
            HTTP_201_CREATED: PostSerializer,
            HTTP_400_BAD_REQUEST: OpenApiResponse(description="Invalid input data"),
            HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(description="Too many requests"),
        },
        examples=[
            OpenApiExample(
                "Create post request",
                value={
                    "title": "My first post",
                    "slug": "my-first-post",
                    "content": "Hello world",
                    "status": "draft",
                },
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["Posts"],
        summary="Retrieve post",
        description="Return a single post by slug.",
        responses={
            HTTP_200_OK: PostSerializer,
            HTTP_404_NOT_FOUND: OpenApiResponse(description="Post not found"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Posts"],
        summary="Update post",
        description="Update a post completely.",
        request=PostSerializer,
        responses={
            HTTP_200_OK: PostSerializer,
            HTTP_400_BAD_REQUEST: OpenApiResponse(description="Invalid input data"),
            HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            HTTP_403_FORBIDDEN: OpenApiResponse(description="Forbidden"),
            HTTP_404_NOT_FOUND: OpenApiResponse(description="Post not found"),
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["Posts"],
        summary="Partially update post",
        description="Update selected fields of a post.",
        request=PostSerializer,
        responses={
            HTTP_200_OK: PostSerializer,
            HTTP_400_BAD_REQUEST: OpenApiResponse(description="Invalid input data"),
            HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            HTTP_403_FORBIDDEN: OpenApiResponse(description="Forbidden"),
            HTTP_404_NOT_FOUND: OpenApiResponse(description="Post not found"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=["Posts"],
        summary="Delete post",
        description="Delete a post.",
        responses={
            HTTP_204_NO_CONTENT: OpenApiResponse(description="Post deleted successfully"),
            HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            HTTP_403_FORBIDDEN: OpenApiResponse(description="Forbidden"),
            HTTP_404_NOT_FOUND: OpenApiResponse(description="Post not found"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def _publish_post_published(self, post):
        """Push a post-published event to all SSE subscribers via Redis Pub/Sub."""
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
        redis_conn.publish(_REDIS_PUBSUB_CHANNEL, payload)

    def perform_create(self, serializer):
        logger.info("Post create attempt by user_id=%s", self.request.user.id)
        serializer.save(author=self.request.user)
        invalidate_posts_cache.delay()
        logger.info(
            "Post created by user_id=%s slug=%s",
            self.request.user.id,
            serializer.instance.slug,
        )
        if serializer.instance.status == Post.Status.PUBLISHED:
            self._publish_post_published(serializer.instance)

    def perform_update(self, serializer):
        post = self.get_object()
        was_published = post.status == Post.Status.PUBLISHED
        logger.info(
            "Post update attempt user_id=%s slug=%s",
            self.request.user.id,
            post.slug,
        )
        serializer.save()
        invalidate_posts_cache.delay()
        logger.info(
            "Post updated user_id=%s slug=%s",
            self.request.user.id,
            post.slug,
        )
        # Fire an event only when transitioning draft → published (not on
        # every re-save of an already-published post).
        if serializer.instance.status == Post.Status.PUBLISHED and not was_published:
            self._publish_post_published(serializer.instance)

    def perform_destroy(self, instance):
        logger.info(
            "Post delete attempt user_id=%s slug=%s",
            self.request.user.id,
            instance.slug,
        )
        instance.delete()
        invalidate_posts_cache.delay()
        logger.info(
            "Post deleted user_id=%s slug=%s",
            self.request.user.id,
            instance.slug,
        )

    @extend_schema(
        tags=["Comments"],
        summary="List or create comments",
        description="""
        GET returns comments for a post.
        POST creates a new comment for a post.

        **Authorization required for POST**
        """,
        request=CommentSerializer,
        responses={
            HTTP_200_OK: CommentSerializer(many=True),
            HTTP_201_CREATED: CommentSerializer,
            HTTP_400_BAD_REQUEST: OpenApiResponse(description="Invalid input data"),
            HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            HTTP_404_NOT_FOUND: OpenApiResponse(description="Post not found"),
        },
        examples=[
            OpenApiExample(
                "Create comment request",
                value={
                    "body": "Nice post!"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Create comment response",
                value={
                    "id": 1,
                    "body": "Nice post!",
                },
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, slug=None):
        post = self.get_object()

        if request.method == "GET":
            qs = Comment.objects.filter(post=post).order_by("-created_at")
            return Response(CommentSerializer(qs, many=True).data)

        logger.info(
            "Comment create attempt user_id=%s post_slug=%s",
            request.user.id,
            post.slug,
        )

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user, post=post)

        # Offload all comment side-effects (Notification creation + WebSocket
        # broadcast) to a Celery task so the HTTP response is not delayed.
        process_new_comment.delay(serializer.instance.id)

        logger.info(
            "Comment created user_id=%s post_slug=%s comment_id=%s",
            request.user.id,
            post.slug,
            serializer.instance.id,
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
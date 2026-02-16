import json
import logging
from urllib.parse import urlencode

from django.core.cache import cache
from django.db.models import QuerySet
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Post, Comment
from .permissions import IsOwnerOrReadOnly
from .serializers import PostSerializer, CommentSerializer
from .throttles import PostCreateUserThrottle

logger = logging.getLogger("blog")


class PostViewSet(ModelViewSet):
    serializer_class = PostSerializer
    lookup_field = "slug"
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_throttles(self):
        if self.action == "create":
            return [PostCreateUserThrottle()]
        return []

    def get_queryset(self) -> QuerySet:
        # Anyone can read only published posts
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return Post.objects.filter(status=Post.Status.PUBLISHED)
        return Post.objects.all()

    def _bump_posts_list_cache_version(self):
        try:
            cache.incr("posts:list:version")
        except ValueError:
            cache.set("posts:list:version", 2, None)

    def list(self, request, *args, **kwargs):
        # Manual cache (instead of cache_page) because we need explicit invalidation on create/update.
        version = cache.get("posts:list:version")
        if version is None:
            cache.set("posts:list:version", 1, None)
            version = 1

        params = request.query_params.dict()
        params_str = urlencode(sorted(params.items()))
        cache_key = f"posts:list:v{version}:{params_str}"

        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Posts list cache hit key=%s", cache_key)
            return Response(cached)

        logger.debug("Posts list cache miss key=%s", cache_key)
        response = super().list(request, *args, **kwargs)

        if response.status_code == 200:
            cache.set(cache_key, response.data, 60)

        return response

    def perform_create(self, serializer):
        logger.info("Post create attempt by user_id=%s", self.request.user.id)
        serializer.save(author=self.request.user)
        self._bump_posts_list_cache_version()
        logger.info(
            "Post created by user_id=%s slug=%s",
            self.request.user.id,
            serializer.instance.slug,
        )

    def perform_update(self, serializer):
        post = self.get_object()
        logger.info(
            "Post update attempt user_id=%s slug=%s",
            self.request.user.id,
            post.slug,
        )
        serializer.save()
        self._bump_posts_list_cache_version()
        logger.info(
            "Post updated user_id=%s slug=%s",
            self.request.user.id,
            post.slug,
        )

    def perform_destroy(self, instance):
        logger.info(
            "Post delete attempt user_id=%s slug=%s",
            self.request.user.id,
            instance.slug,
        )
        instance.delete()
        self._bump_posts_list_cache_version()
        logger.info(
            "Post deleted user_id=%s slug=%s",
            self.request.user.id,
            instance.slug,
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

        # REDIS PUB/SUB (publish event on comment creation)
        redis_conn = get_redis_connection("default")
        event = {
            "comment_id": serializer.instance.id,
            "post_slug": post.slug,
            "author_id": request.user.id,
            "created_at": serializer.instance.created_at.isoformat(),
        }
        redis_conn.publish("comments", json.dumps(event))

        logger.info(
            "Comment created user_id=%s post_slug=%s comment_id=%s",
            request.user.id,
            post.slug,
            serializer.instance.id,
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

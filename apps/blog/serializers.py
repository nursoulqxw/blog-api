#Python modules
import logging
import pytz

#Django modules
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

#Django REST modules
from rest_framework import serializers

#Project modules
from .models import Category, Tag, Post, Comment


logger = logging.getLogger("blog")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class PostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source="tags",
        many=True,
        write_only=True,
        required=False,
    )
    # Locale-aware, timezone-converted timestamps.
    # Anonymous users see UTC ISO format; authenticated users see
    # dates formatted according to their timezone and locale.
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "category_id",
            "tags",
            "tag_ids",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    # ------------------------------------------------------------------
    # Date helpers
    # ------------------------------------------------------------------

    def _localize_dt(self, dt) -> str:
        """
        Convert *dt* to the request user's timezone and format it
        using the active locale's DATETIME_FORMAT.

        Falls back to UTC ISO 8601 for anonymous requests or if the
        user's timezone is invalid.
        """
        if dt is None:
            return None

        request = self.context.get("request")
        user_tz = pytz.UTC

        if request and getattr(request, "user", None) and request.user.is_authenticated:
            tz_name = getattr(request.user, "timezone", "UTC") or "UTC"
            try:
                user_tz = pytz.timezone(tz_name)
            except pytz.exceptions.UnknownTimeZoneError:
                pass

        local_dt = dt.astimezone(user_tz)
        # Django's date_format() respects the currently active language
        # for month names, weekday names, etc.
        try:
            return date_format(local_dt, format="DATETIME_FORMAT", use_l10n=True)
        except Exception:
            return local_dt.isoformat()

    def get_created_at(self, obj: Post) -> str:
        return self._localize_dt(obj.created_at)

    def get_updated_at(self, obj: Post) -> str:
        return self._localize_dt(obj.updated_at)

    def create(self, validated_data: dict) -> Post:
        logger.debug("PostSerializer.create called")
        return super().create(validated_data)

    def update(self, instance: Post, validated_data: dict) -> Post:
        logger.debug("PostSerializer.update called for slug=%s", instance.slug)
        return super().update(instance, validated_data)


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "author", "body", "created_at")
        read_only_fields = ("id", "author", "created_at")
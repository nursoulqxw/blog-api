from rest_framework import serializers
from .models import Category, Tag, Post, Comment

class CategorySerializer(serializers.Serializer):
    class Meta:
        model = Category
        fields = {"id", "name", "slug"}

class TagSerializer(serializers.Serializer):
    class Meta:
        model = Tag
        fields = {"id", "name", "slug"}

class PostSerializer(serializers.Serializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "tags",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "author", "body", "created_at")
        read_only_fields = ("id", "author", "created_at")
# Django modules
from django.contrib.auth import get_user_model
from django.utils.translation import gettext

# Django REST Framework
from rest_framework.serializers import (
    Serializer,
    ModelSerializer,
    EmailField,
    CharField,
)
from rest_framework.exceptions import ValidationError

from .validators import validate_language, validate_timezone


User = get_user_model()


class UserSerializer(ModelSerializer):
    """
    Serializer for user data.
    """

    class Meta:
        """
        Customization of the serializer metadata.
        """

        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "date_joined",
            "preferred_language",
            "timezone",
        )
        read_only_fields = fields


class RegisterSerializer(Serializer):
    """
    Serializer for user registration.
    """

    email = EmailField(required=True)
    first_name = CharField(required=True, max_length=50)
    last_name = CharField(required=True, max_length=50)
    password = CharField(required=True, write_only=True, min_length=8)
    password2 = CharField(required=True, write_only=True, min_length=8)

    class Meta:
        """
        Customization of the serializer metadata.
        """

        fields = (
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
        )

    def validate_email(self, value: str) -> str:
        """
        Validates the email field.
        """

        value = (value or "").lower().strip()

        if not value:
            raise ValidationError(
                detail={
                    "email": [gettext("This field is required.")]
                }
            )

        if User.objects.filter(email=value).exists():
            raise ValidationError(
                detail={
                    "email": [gettext("User with this email already exists.")]
                }
            )

        return value

    def validate(self, attrs: dict) -> dict:
        """
        Validates the input data.
        """

        email = attrs.get("email")
        password = attrs.get("password")
        password2 = attrs.get("password2")

        if not email:
            raise ValidationError(
                detail={
                    "email": [gettext("This field is required.")]
                }
            )

        attrs["email"] = email.lower().strip()

        if password != password2:
            raise ValidationError(
                detail={
                    "password2": [gettext("Passwords do not match.")]
                }
            )

        return super().validate(attrs)

    def create(self, validated_data: dict):
        """
        Creates a new user.
        """

        validated_data.pop("password2")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data,
        )

        return user


class TimezoneSerializer(Serializer):
    """
    Serializer for changing timezone.
    """

    timezone = CharField(validators=[validate_timezone])


class LanguageSerializer(Serializer):
    """
    Serializer for changing preferred language.
    """

    preferred_language = CharField(validators=[validate_language])
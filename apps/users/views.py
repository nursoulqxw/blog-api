import logging
import threading

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    LanguageSerializer,
    TimezoneSerializer,
)
from .throttles import RegisterIPThrottle


logger = logging.getLogger("users")


class RegisterViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterIPThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Register a new user",
        description="""
        Create a new user account and return user data with JWT tokens.

        **Validation:**
        - `email` must be unique
        - passwords must match
        - all required fields must be provided

        **Rate limit:**
        - limited by IP address

        **Response:**
        - user info
        - refresh token
        - access token
        """,
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="User registered successfully",
                examples=[
                    OpenApiExample(
                        "Successful registration",
                        value={
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "first_name": "John",
                                "last_name": "Doe",
                                "avatar": None,
                                "date_joined": "2026-03-15T10:00:00Z",
                            },
                            "tokens": {
                                "refresh": "refresh_token_here",
                                "access": "access_token_here",
                            },
                            "detail": "User registered successfully.",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Invalid input data",
                examples=[
                    OpenApiExample(
                        "Passwords do not match",
                        value={
                            "password": ["Passwords do not match."]
                        },
                    ),
                    OpenApiExample(
                        "Email already exists",
                        value={
                            "email": ["User with this email already exists."]
                        },
                    ),
                ],
            ),
            429: OpenApiResponse(
                description="Too many requests",
                examples=[
                    OpenApiExample(
                        "Rate limit exceeded",
                        value={
                            "detail": "Request was throttled. Expected available in 60 seconds."
                        },
                    )
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Register request",
                value={
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "password": "StrongPass123",
                    "password2": "StrongPass123",
                },
            )
        ],
    )
    def create(self, request):
        logger.info("Registration attempt for email: %s", request.data.get("email"))

        try:
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        except Exception:
            logger.exception(
                "Registration failed for email: %s",
                request.data.get("email"),
            )
            raise

        refresh = RefreshToken.for_user(user)

        logger.info("User registered: %s", user.email)

        # Send welcome email in the user's chosen language.
        # Runs in a background thread so the HTTP response is not delayed
        # by email delivery (console backend is instant, SMTP can be slow).
        threading.Thread(
            target=_send_welcome_email,
            args=(user,),
            daemon=True,
        ).start()

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "detail": _("User registered successfully."),
            },
            status=status.HTTP_201_CREATED,
        )


class UserPreferencesViewSet(viewsets.ViewSet):
    """
    Manage user preferences.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Update user language",
        description="""
        Update authenticated user's preferred language.

        **Authorization required:** Bearer token

        **Validation:**
        - `preferred_language` must be one of the supported languages

        **Response:**
        - success message
        - updated preferred language
        """,
        request=LanguageSerializer,
        responses={
            200: OpenApiResponse(
                description="Language updated successfully",
                examples=[
                    OpenApiExample(
                        "Success response",
                        value={
                            "message": "Language successfully updated.",
                            "preferred_language": "ru",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Invalid language",
                examples=[
                    OpenApiExample(
                        "Invalid language example",
                        value={
                            "preferred_language": ["This language is not supported."]
                        },
                    )
                ],
            ),
            401: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Update language request",
                value={
                    "preferred_language": "ru"
                },
            )
        ],
    )
    @action(detail=False, methods=["patch"], url_path="language")
    def update_language(self, request):
        """
        PATCH /api/auth/preferences/language/
        """

        serializer = LanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request.user.preferred_language = serializer.validated_data["preferred_language"]
        request.user.save(update_fields=["preferred_language"])

        logger.info(
            "User %s changed language to %s",
            request.user.email,
            request.user.preferred_language,
        )

        return Response(
            {
                "message": _("Language successfully updated."),
                "preferred_language": request.user.preferred_language,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Auth"],
        summary="Update user timezone",
        description="""
        Update authenticated user's timezone.

        **Authorization required:** Bearer token

        **Validation:**
        - `timezone` must be a valid IANA timezone

        **Response:**
        - success message
        - updated timezone
        """,
        request=TimezoneSerializer,
        responses={
            200: OpenApiResponse(
                description="Timezone updated successfully",
                examples=[
                    OpenApiExample(
                        "Success response",
                        value={
                            "message": "Timezone successfully updated.",
                            "timezone": "Asia/Almaty",
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Invalid timezone",
                examples=[
                    OpenApiExample(
                        "Invalid timezone example",
                        value={
                            "timezone": ["Enter a valid timezone."]
                        },
                    )
                ],
            ),
            401: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Update timezone request",
                value={
                    "timezone": "Asia/Almaty"
                },
            )
        ],
    )
    @action(detail=False, methods=["patch"], url_path="timezone")
    def update_timezone(self, request):
        """
        PATCH /api/auth/preferences/timezone/
        """

        serializer = TimezoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request.user.timezone = serializer.validated_data["timezone"]
        request.user.save(update_fields=["timezone"])

        logger.info(
            "User %s changed timezone to %s",
            request.user.email,
            request.user.timezone,
        )

        return Response(
            {
                "message": _("Timezone successfully updated."),
                "timezone": request.user.timezone,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send_welcome_email(user) -> None:
    """
    Render and send a welcome email in the *user's* preferred language.

    The language is activated explicitly before rendering so the email
    language is independent of whatever language is active in the current
    request thread (a key hw2 requirement).
    """
    lang = getattr(user, "preferred_language", "en") or "en"

    with translation.override(lang):
        subject = render_to_string(
            "emails/welcome/subject.txt",
            {"user": user},
        ).strip()

        body = render_to_string(
            "emails/welcome/body.txt",
            {"user": user},
        )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Welcome email sent to %s (lang=%s)", user.email, lang)
    except Exception:
        logger.exception("Failed to send welcome email to %s", user.email)
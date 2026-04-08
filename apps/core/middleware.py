"""
Language and timezone middleware.

Priority for language detection:
  1. Authenticated user's saved preferred_language (from JWT or session)
  2. ?lang= query parameter
  3. Accept-Language HTTP header
  4. Default language (en)
"""
import logging

import pytz
from django.utils import timezone, translation

logger = logging.getLogger("core")

SUPPORTED_LANGUAGES = ["en", "ru", "kk"]
DEFAULT_LANGUAGE = "en"


class LanguageTimezoneMiddleware:
    """
    Activates the correct language and timezone for every request.

    For JWT-authenticated requests the Authorization header is decoded
    (without an extra round-trip once DRF caches the user) so that the
    user's saved preferences are applied from the very start of the
    request/response cycle.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = self._resolve_user(request)
        lang = self._resolve_language(request, user)
        tz = self._resolve_timezone(user)

        translation.activate(lang)
        request.LANGUAGE_CODE = lang

        if tz is not None:
            timezone.activate(tz)
        else:
            timezone.deactivate()

        response = self.get_response(request)
        translation.deactivate()
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_user(self, request):
        """
        Return the authenticated user or None.

        * Session-auth:  request.user is already populated by Django's
          AuthenticationMiddleware (which runs before this middleware).
        * JWT-auth:      DRF resolves the user at view time, so we decode
          the token ourselves here to read preferences early.
        """
        # Session / already-resolved user
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            return request.user

        # JWT Bearer token
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if auth.startswith("Bearer "):
            return self._user_from_jwt(auth.split(" ", 1)[1])

        return None

    def _user_from_jwt(self, token_str: str):
        """Decode the JWT and return the matching User, or None on any error."""
        try:
            from django.contrib.auth import get_user_model
            from rest_framework_simplejwt.tokens import AccessToken

            token = AccessToken(token_str)
            User = get_user_model()
            return User.objects.get(id=token["user_id"])
        except Exception:
            return None

    def _resolve_language(self, request, user) -> str:
        # 1. User's stored preference
        if user is not None:
            lang = getattr(user, "preferred_language", None)
            if lang and lang in SUPPORTED_LANGUAGES:
                return lang

        # 2. ?lang= query parameter
        lang = request.GET.get("lang", "").strip().lower()
        if lang in SUPPORTED_LANGUAGES:
            return lang

        # 3. Accept-Language header  (e.g. "ru-RU,ru;q=0.9,en;q=0.8")
        accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        for part in accept.split(","):
            code = part.strip().split(";")[0].strip().split("-")[0].lower()
            if code in SUPPORTED_LANGUAGES:
                return code

        # 4. Default
        return DEFAULT_LANGUAGE

    def _resolve_timezone(self, user):
        """Return a pytz timezone for the user, or None for anonymous."""
        if user is None:
            return None
        tz_name = getattr(user, "timezone", "UTC") or "UTC"
        try:
            return pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning("Unknown timezone '%s' for user %s", tz_name, user)
            return pytz.UTC
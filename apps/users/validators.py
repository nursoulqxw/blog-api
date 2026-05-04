#Python modules
import pytz
from django.utils.translation import gettext as _

#Django REST modules
from rest_framework.exceptions import ValidationError


SUPPORTED_LANGUAGES = ["en", "ru", "kk"]


def validate_language(value: str) -> str:
    value = (value or "").strip().lower()

    if value not in SUPPORTED_LANGUAGES:
        raise ValidationError(_("Unsupported language."))

    return value


def validate_timezone(value: str) -> str:
    value = (value or "").strip()

    if value not in pytz.all_timezones:
        raise ValidationError(_("Invalid timezone."))

    return value
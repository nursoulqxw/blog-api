#Python modules
import logging
from celery import shared_task

#Django modules
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation

logger = logging.getLogger("users")

# Retries are important for email tasks because SMTP servers can be temporarily
# unavailable, rate-limit connections, or drop connections mid-send. Retrying
# with exponential backoff prevents hammering the server and ensures the welcome
# email is eventually delivered without requiring manual intervention.

@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_welcome_email(user_id: int) -> str:
    from apps.users.models import User

    user = User.objects.get(pk=user_id)
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

    send_mail(
        subject=subject,
        message=body,
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info("Welcome email sent to %s (lang=%s)", user.email, lang)
    return f"Email sent to {user.email}"

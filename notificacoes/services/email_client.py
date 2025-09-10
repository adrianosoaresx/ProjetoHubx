import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(user, subject: str, body: str) -> None:
    """Enviar e-mail usando backend configurado."""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception as exc:  # pragma: no cover - falha de integração
        logger.exception(
            "erro_email",
            extra={"user": getattr(user, "id", None)},
        )
        raise
    else:
        logger.info("email_enviado", extra={"user": getattr(user, "id", None)})

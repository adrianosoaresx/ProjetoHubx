import logging
from django.conf import settings

try:  # pragma: no cover - dependência externa
    from twilio.rest import Client as TwilioClient  # type: ignore
except Exception:  # pragma: no cover - módulo não instalado
    TwilioClient = None  # type: ignore


logger = logging.getLogger(__name__)


def _credentials_configured() -> bool:
    return all(getattr(settings, attr, None) for attr in ("TWILIO_SID", "TWILIO_TOKEN", "TWILIO_WHATSAPP_FROM"))


def send_whatsapp(user, message: str) -> None:
    """Enviar mensagem WhatsApp usando Twilio."""
    if not _credentials_configured() or TwilioClient is None:
        logger.warning(
            "whatsapp_indisponivel",
            extra={"user": getattr(user, "id", None)},
        )
        raise RuntimeError("WhatsApp indisponível")

    try:
        client = TwilioClient(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{user.whatsapp}",
        )
    except Exception as exc:  # pragma: no cover - falha de integração
        logger.exception(
            "erro_whatsapp",
            extra={"user": getattr(user, "id", None)},
        )
        raise
    else:
        logger.info("whatsapp_enviado", extra={"user": getattr(user, "id", None)})

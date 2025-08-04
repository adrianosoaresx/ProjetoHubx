import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_whatsapp(user, message: str) -> None:
    """Enviar mensagem WhatsApp usando Twilio."""
    try:
        from twilio.rest import Client as TwilioClient  # type: ignore
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

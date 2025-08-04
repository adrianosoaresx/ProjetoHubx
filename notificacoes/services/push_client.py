import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_push(user, message: str) -> None:
    """Enviar push usando OneSignal."""
    try:
        from onesignal_sdk.client import Client as OneSignalClient  # type: ignore
        client = OneSignalClient(app_id=settings.ONESIGNAL_APP_ID, rest_api_key=settings.ONESIGNAL_API_KEY)
        client.send_notification({
            "contents": {"en": message},
            "include_external_user_ids": [str(user.id)],
        })
    except Exception as exc:  # pragma: no cover - falha de integração
        logger.exception(
            "erro_push",
            extra={"user": getattr(user, "id", None)},
        )
        raise
    else:
        logger.info("push_enviado", extra={"user": getattr(user, "id", None)})

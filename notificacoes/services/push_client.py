import logging

from django.conf import settings

from ..models import PushSubscription

try:  # pragma: no cover - lib externa
    from onesignal_sdk.error import OneSignalHTTPError  # type: ignore
except Exception:  # pragma: no cover - fallback quando lib não instalada
    class OneSignalHTTPError(Exception):  # type: ignore
        status_code = None
        http_response = None


logger = logging.getLogger(__name__)


def send_push(user, message: str) -> None:
    """Enviar push usando OneSignal."""
    try:
        from onesignal_sdk.client import Client as OneSignalClient  # type: ignore
        client = OneSignalClient(app_id=settings.ONESIGNAL_APP_ID, rest_api_key=settings.ONESIGNAL_API_KEY)
        client.send_notification(
            {
                "contents": {"en": message},
                "include_external_user_ids": [str(user.id)],
            }
        )
    except OneSignalHTTPError as exc:  # pragma: no cover - lib externa
        status = getattr(exc, "status_code", None)
        if status in {404, 410}:
            errors: list[str] = []
            try:
                errors = exc.http_response.json().get("errors", [])
            except Exception:  # pragma: no cover - resposta inesperada
                errors = []
            subs = PushSubscription.objects.filter(user=user, ativo=True)
            for sub in subs:
                if any(str(sub.device_id) in str(err) for err in errors):
                    sub.ativo = False
                    sub.save(update_fields=["ativo"])
                    logger.info(
                        "push_inscricao_inativa",
                        extra={"user": getattr(user, "id", None), "device_id": sub.device_id},
                    )
        else:
            logger.exception("erro_push", extra={"user": getattr(user, "id", None)})
            raise
    except Exception as exc:  # pragma: no cover - falha de integração
        logger.exception(
            "erro_push",
            extra={"user": getattr(user, "id", None)},
        )
        raise
    else:
        logger.info("push_enviado", extra={"user": getattr(user, "id", None)})

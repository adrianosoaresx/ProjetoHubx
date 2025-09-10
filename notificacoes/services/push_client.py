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
    # Se desativado por flag ou não configurado, não tenta enviar e evita quebrar o fluxo
    if not getattr(settings, "ONESIGNAL_ENABLED", False):
        logger.info(
            "push_desativado",
            extra={"user": getattr(user, "id", None)},
        )
        return
    app_id = getattr(settings, "ONESIGNAL_APP_ID", None)
    api_key = getattr(settings, "ONESIGNAL_API_KEY", None)
    if not app_id or not api_key:
        logger.info(
            "push_nao_configurado",
            extra={"user": getattr(user, "id", None)},
        )
        return

    try:
        try:
            from onesignal_sdk.client import Client as OneSignalClient  # type: ignore
        except Exception:  # Lib não instalada/configurada
            logger.info(
                "push_cliente_indisponivel",
                extra={"user": getattr(user, "id", None)},
            )
            return

        client = OneSignalClient(app_id=app_id, rest_api_key=api_key)
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
            return
    except Exception:  # pragma: no cover - falha de integração
        logger.exception(
            "erro_push",
            extra={"user": getattr(user, "id", None)},
        )
        return
    else:
        logger.info("push_enviado", extra={"user": getattr(user, "id", None)})

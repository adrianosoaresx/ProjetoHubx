from __future__ import annotations

import structlog
from celery import shared_task  # type: ignore
from django.contrib.auth import get_user_model

from notificacoes.services.notificacoes import enviar_para_usuario

logger = structlog.get_logger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def enviar_notificacao_conexao_async(
    self,
    user_id: str,
    template_codigo: str,
    context: dict[str, str],
) -> None:
    user = User.objects.filter(id=user_id).first()
    if not user:
        logger.warning(
            "usuario_notificacao_conexao_nao_encontrado",
            user_id=user_id,
            template_codigo=template_codigo,
        )
        return

    try:
        enviar_para_usuario(user, template_codigo, context)
    except Exception:
        logger.exception(
            "falha_envio_notificacao_conexao",
            user_id=user_id,
            template_codigo=template_codigo,
        )
        raise self.retry(countdown=2**self.request.retries)

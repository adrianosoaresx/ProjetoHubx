from __future__ import annotations

from celery import shared_task  # type: ignore

import structlog
from notificacoes.services.notificacoes import enviar_para_usuario

from .models import RespostaDiscussao


logger = structlog.get_logger(__name__)


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_nova_resposta(resposta_id: int) -> None:
    try:
        resposta = (
            RespostaDiscussao.objects.select_related("topico", "topico__autor", "autor")
            .prefetch_related("topico__respostas__autor")
            .get(id=resposta_id)
        )
    except RespostaDiscussao.DoesNotExist:  # pragma: no cover - segurança
        return

    topico = resposta.topico
    destinatarios = {topico.autor, *(r.autor for r in topico.respostas.all())}
    destinatarios.discard(resposta.autor)
    for user in destinatarios:
        try:
            enviar_para_usuario(
                user,
                "discussao_nova_resposta",
                {"topico": topico, "resposta": resposta},
            )
        except Exception as exc:  # pragma: no cover - falha no envio
            logger.warning(
                "notificar_nova_resposta_falha",
                user_id=getattr(user, "id", None),
                resposta_id=resposta.id,
                error=str(exc),
            )
            if not isinstance(exc, ValueError):
                raise
        else:
            logger.info(
                "notificar_nova_resposta_sucesso",
                user_id=user.id,
                resposta_id=resposta.id,
            )


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_melhor_resposta(resposta_id: int) -> None:
    try:
        resposta = RespostaDiscussao.objects.select_related("autor", "topico").get(id=resposta_id)
    except RespostaDiscussao.DoesNotExist:  # pragma: no cover - segurança
        return

    try:
        enviar_para_usuario(
            resposta.autor,
            "discussao_melhor_resposta",
            {"topico": resposta.topico, "resposta": resposta},
        )
    except Exception as exc:  # pragma: no cover - falha no envio
        logger.warning(
            "notificar_melhor_resposta_falha",
            user_id=resposta.autor_id,
            resposta_id=resposta.id,
            error=str(exc),
        )
        if not isinstance(exc, ValueError):
            raise
    else:
        logger.info(
            "notificar_melhor_resposta_sucesso",
            user_id=resposta.autor_id,
            resposta_id=resposta.id,
        )

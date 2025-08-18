from __future__ import annotations

import structlog
from celery import shared_task  # type: ignore

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import RespostaDiscussao, TopicoDiscussao


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
        except ValueError:  # pragma: no cover - template ausente
            continue


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
    except ValueError:  # pragma: no cover - template ausente
        return


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_topico_resolvido(topico_id: int) -> None:
    try:
        topico = (
            TopicoDiscussao.objects.select_related("autor")
            .prefetch_related("respostas__autor")
            .get(id=topico_id)
        )
    except TopicoDiscussao.DoesNotExist:  # pragma: no cover - segurança
        return

    destinatarios = {topico.autor, *(r.autor for r in topico.respostas.all())}
    for user in destinatarios:
        try:
            enviar_para_usuario(
                user,
                "discussao_topico_resolvido",
                {"topico": topico},
            )
            logger.info(
                "topico_resolvido_notificacao_enviada",
                topico_id=topico.id,
                user_id=user.id,
            )
        except ValueError:  # pragma: no cover - template ausente
            continue

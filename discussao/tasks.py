from __future__ import annotations

from celery import shared_task

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import RespostaDiscussao


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_nova_resposta(resposta_id: int) -> None:
    resposta = RespostaDiscussao.objects.select_related("topico", "topico__autor", "autor").get(
        pk=resposta_id
    )
    topico = resposta.topico
    if resposta.autor_id != topico.autor_id:
        try:
            enviar_para_usuario(
                topico.autor,
                "discussao_nova_resposta",
                {"topico": topico.titulo, "autor": resposta.autor.get_full_name() or resposta.autor.username},
            )
        except ValueError:
            pass


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_melhor_resposta(resposta_id: int) -> None:
    resposta = RespostaDiscussao.objects.select_related("autor", "topico").get(pk=resposta_id)
    try:
        enviar_para_usuario(
            resposta.autor,
            "discussao_melhor_resposta",
            {"topico": resposta.topico.titulo},
        )
    except ValueError:
        pass

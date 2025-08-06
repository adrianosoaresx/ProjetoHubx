from __future__ import annotations

from celery import shared_task  # type: ignore

from .models import RespostaDiscussao


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_nova_resposta(resposta_id: int) -> None:
    try:
        RespostaDiscussao.objects.select_related("topico", "topico__autor").get(id=resposta_id)
    except RespostaDiscussao.DoesNotExist:  # pragma: no cover - segurança
        return


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_melhor_resposta(resposta_id: int) -> None:
    try:
        RespostaDiscussao.objects.select_related("autor").get(id=resposta_id)
    except RespostaDiscussao.DoesNotExist:  # pragma: no cover - segurança
        return

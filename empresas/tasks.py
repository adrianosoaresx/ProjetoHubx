from __future__ import annotations

from celery import shared_task
from django.dispatch import Signal, receiver

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import AvaliacaoEmpresa

nova_avaliacao = Signal()  # args: avaliacao


@shared_task
def notificar_responsavel(avaliacao_id: str) -> None:
    avaliacao = AvaliacaoEmpresa.objects.select_related("empresa__usuario").get(pk=avaliacao_id)
    email = avaliacao.empresa.usuario.email
    if email:
        enviar_para_usuario(
            avaliacao.empresa.usuario,
            "nova_avaliacao_empresa",
            {"empresa": avaliacao.empresa.nome},
        )


@receiver(nova_avaliacao)
def _on_nova_avaliacao(sender, avaliacao: AvaliacaoEmpresa, **kwargs) -> None:
    notificar_responsavel.delay(str(avaliacao.id))

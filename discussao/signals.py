from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import InteracaoDiscussao, RespostaDiscussao, TopicoDiscussao


def _broadcast(topico_id: int, data: dict) -> None:
    layer = get_channel_layer()
    if not layer:  # pragma: no cover - layer ausente
        return
    async_to_sync(layer.group_send)(f"discussao_{topico_id}", {"type": "broadcast", "data": data})


@receiver(post_save, sender=RespostaDiscussao)
def resposta_nova(sender, instance: RespostaDiscussao, created: bool, **kwargs) -> None:
    if created:
        _broadcast(
            instance.topico_id,
            {
                "evento": "nova_resposta",
                "topico_id": instance.topico_id,
                "resposta_id": instance.id,
                "conteudo": instance.conteudo[:100],
            },
        )


@receiver([post_save, post_delete], sender=InteracaoDiscussao)
def interacao_atualizada(sender, instance: InteracaoDiscussao, **kwargs) -> None:
    obj = instance.content_object
    topico_id = obj.id if isinstance(obj, TopicoDiscussao) else obj.topico_id
    _broadcast(
        topico_id,
        {
            "evento": "atualizacao_votos",
            "topico_id": topico_id,
            "score": obj.score,
            "num_votos": obj.num_votos,
        },
    )


@receiver(post_save, sender=TopicoDiscussao)
def topico_resolucao(sender, instance: TopicoDiscussao, **kwargs) -> None:
    update_fields = kwargs.get("update_fields")
    if update_fields and {"melhor_resposta", "resolvido"}.intersection(update_fields):
        _broadcast(
            instance.pk,
            {
                "evento": "resolucao",
                "topico_id": instance.pk,
                "resolvido": instance.resolvido,
                "melhor_resposta": instance.melhor_resposta_id,
            },
        )

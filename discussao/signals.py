from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import InteracaoDiscussao, RespostaDiscussao


def _send_event(group: str, event: dict) -> None:
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(group, {"type": "discussion.event", **event})


@receiver(post_save, sender=RespostaDiscussao)
def resposta_created(sender, instance: RespostaDiscussao, created: bool, **kwargs) -> None:
    if not created:
        return
    _send_event(
        f"discussao_{instance.topico_id}",
        {
            "event": "nova_resposta",
            "topico_id": instance.topico_id,
            "resposta_id": instance.id,
            "conteudo": instance.conteudo[:100],
        },
    )


@receiver([post_save, post_delete], sender=InteracaoDiscussao)
def interacao_changed(sender, instance: InteracaoDiscussao, **kwargs) -> None:
    obj = instance.content_object
    if hasattr(obj, "topico_id"):
        topico_id = getattr(obj, "topico_id", obj.id)
    else:
        topico_id = obj.id
    _send_event(
        f"discussao_{topico_id}",
        {
            "event": "atualizacao_votos",
            "objeto": obj.__class__.__name__,
            "objeto_id": obj.id,
            "score": getattr(obj, "score", 0),
        },
    )

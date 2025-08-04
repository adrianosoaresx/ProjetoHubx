from __future__ import annotations

from celery import shared_task

from .models import Post
from notificacoes.services.notificacoes import enviar_para_usuario


@shared_task
def notificar_autor_sobre_interacao(post_id: str, tipo: str) -> None:
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:  # pragma: no cover - simples
        return
    event = "feed_like" if tipo == "like" else "feed_comment"
    try:
        enviar_para_usuario(post.autor, event, {"post_id": str(post.id)})
    except Exception:  # pragma: no cover - melhor esforço
        pass

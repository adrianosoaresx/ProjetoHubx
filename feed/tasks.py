from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache
from prometheus_client import Counter, Histogram

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import Post

POSTS_CREATED = Counter("feed_posts_created_total", "Total de posts criados")
NOTIFICATIONS_SENT = Counter(
    "feed_notifications_sent_total", "Total de notificações de novos posts"
)
NOTIFICATION_LATENCY = Histogram(
    "feed_notification_latency_seconds", "Latência do envio de notificações"
)


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


@shared_task
def notify_new_post(post_id: str) -> None:
    # garante idempotência: apenas primeira execução envia
    if not cache.add(f"notify_post_{post_id}", True, 3600):
        return
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:  # pragma: no cover - simples
        return
    User = get_user_model()
    users = User.objects.filter(organizacao=post.organizacao).exclude(id=post.autor_id)
    with NOTIFICATION_LATENCY.time():
        for user in users:
            try:
                enviar_para_usuario(user, "feed_new_post", {"post_id": str(post.id)})
                NOTIFICATIONS_SENT.inc()
            except Exception:  # pragma: no cover - melhor esforço
                pass


@shared_task
def notify_post_moderated(post_id: str, status: str) -> None:
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:  # pragma: no cover - simples
        return
    try:
        enviar_para_usuario(
            post.autor, "feed_post_moderated", {"post_id": str(post.id), "status": status}
        )
    except Exception:  # pragma: no cover - melhor esforço
        pass

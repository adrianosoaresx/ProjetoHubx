from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache
from prometheus_client import Counter, Histogram
from sentry_sdk import capture_exception
from botocore.exceptions import ClientError
import logging

from notificacoes.services.notificacoes import enviar_para_usuario
from organizacoes.models import Organizacao

from datetime import timedelta

from django.utils import timezone

from feed.application.plugins_loader import load_plugins_for

from .models import FeedPluginConfig, Post


logger = logging.getLogger(__name__)

POSTS_CREATED = Counter("feed_posts_created_total", "Total de posts criados")
NOTIFICATIONS_SENT = Counter(
    "feed_notifications_sent_total", "Total de notificações de novos posts"
)
NOTIFICATION_LATENCY = Histogram(
    "feed_notification_latency_seconds", "Latência do envio de notificações"
)


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notificar_autor_sobre_interacao(post_id: str, tipo: str) -> None:
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:  # pragma: no cover - simples
        return
    event = "feed_like" if tipo == "like" else "feed_comment"
    try:
        enviar_para_usuario(post.autor, event, {"post_id": str(post.id)})
        NOTIFICATIONS_SENT.inc()
    except Exception as exc:  # pragma: no cover - melhor esforço
        capture_exception(exc)
        raise



@shared_task(autoretry_for=(Exception,), retry_backoff=True)
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
            except Exception as exc:  # pragma: no cover - melhor esforço
                capture_exception(exc)
                raise


@shared_task(autoretry_for=(Exception,), retry_backoff=True)
def notify_post_moderated(post_id: str, status: str) -> None:
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:  # pragma: no cover - simples
        return
    try:
        enviar_para_usuario(
            post.autor, "feed_post_moderated", {"post_id": str(post.id), "status": status}
        )
        NOTIFICATIONS_SENT.inc()
    except Exception as exc:  # pragma: no cover - melhor esforço
        capture_exception(exc)
        raise

@shared_task(
    autoretry_for=(ClientError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def upload_media(data: bytes, name: str, content_type: str) -> str | tuple[str, str]:
    from django.core.files.uploadedfile import SimpleUploadedFile
    from .services import _upload_media

    file = SimpleUploadedFile(name, data, content_type=content_type)
    try:
        return _upload_media(file)
    except Exception as exc:  # pragma: no cover - melhor esforço
        capture_exception(exc)
        raise


@shared_task
def finalize_upload(result: str | tuple[str, str], pending_id: str) -> None:
    """Atualiza posts com o resultado do upload assíncrono."""

    from django.db.models import Q

    from .models import PendingUpload, Post

    try:
        pending = PendingUpload.objects.get(id=pending_id)
    except PendingUpload.DoesNotExist:  # pragma: no cover - simples
        return

    key = result
    preview_key = None
    if isinstance(result, (list, tuple)):
        key, preview_key = result

    identifier = f"pending:{pending_id}"
    posts = Post.objects.filter(Q(image=identifier) | Q(pdf=identifier) | Q(video=identifier))
    for post in posts:
        updated_fields = []
        if post.image == identifier:
            post.image = key
            updated_fields.append("image")
        if post.pdf == identifier:
            post.pdf = key
            updated_fields.append("pdf")
        if post.video == identifier:
            post.video = key
            updated_fields.append("video")
            if preview_key:
                post.video_preview = preview_key
                updated_fields.append("video_preview")
        if updated_fields:
            post.save(update_fields=updated_fields)

    pending.delete()



@shared_task
def executar_plugins() -> None:
    """Carrega e executa plugins registrados para organizações.

    A tarefa é idempotente e pode ser agendada periodicamente pelo
    ``celery beat`` para que os plugins sejam executados de acordo com o
    intervalo configurado.
    """

    User = get_user_model()
    orgs = Organizacao.objects.filter(feed_plugins__isnull=False).distinct()
    for org in orgs:
        user = User.objects.filter(organizacao=org).first()
        if not user:
            continue
        configs_list = list(FeedPluginConfig.objects.filter(organizacao=org))
        plugins, configs_list = load_plugins_for(org, configs_list)
        configs = {c.module_path: c for c in configs_list}
        for plugin in plugins:
            module_path = f"{plugin.__class__.__module__}.{plugin.__class__.__name__}"
            config = configs.get(module_path)
            if not config:
                continue
            now = timezone.now()
            if config.last_run and now - config.last_run < timedelta(minutes=config.frequency):
                continue
            try:
                plugin.render(user)
            except Exception as exc:  # pragma: no cover - melhor esforço
                logger.exception("Falha ao executar plugin %s", module_path)
                capture_exception(exc)
                continue
            config.last_run = now
            config.save(update_fields=["last_run"])


from __future__ import annotations

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import sentry_sdk

from .middleware import get_request_info
from .models import (
    ConfiguracaoConta,
    ConfiguracaoContextual,
    ConfiguracaoContaLog,
)
from .services import CACHE_KEY, CONTEXT_CACHE_KEY

CONTA_FIELDS = [
    "receber_notificacoes_email",
    "frequencia_notificacoes_email",
    "receber_notificacoes_whatsapp",
    "frequencia_notificacoes_whatsapp",
    "receber_notificacoes_push",
    "frequencia_notificacoes_push",
    "idioma",
    "tema",
    "hora_notificacao_diaria",
    "hora_notificacao_semanal",
    "dia_semana_notificacao",
]

CONTEXT_FIELDS = [
    "receber_notificacoes_email",
    "frequencia_notificacoes_email",
    "receber_notificacoes_whatsapp",
    "frequencia_notificacoes_whatsapp",
    "receber_notificacoes_push",
    "frequencia_notificacoes_push",
    "idioma",
    "tema",
]


@receiver(pre_save, sender=ConfiguracaoConta)
@receiver(pre_save, sender=ConfiguracaoContextual)
def capture_old_values(sender, instance, **kwargs):
    if instance.pk:
        old = sender.all_objects.get(pk=instance.pk)
        fields = CONTA_FIELDS if sender is ConfiguracaoConta else CONTEXT_FIELDS
        instance._old_values = {f: getattr(old, f) for f in fields}
    else:
        instance._old_values = {}


@receiver(post_save, sender=ConfiguracaoConta)
@receiver(post_save, sender=ConfiguracaoContextual)
@receiver(post_delete, sender=ConfiguracaoContextual)
def log_changes(sender, instance, created=False, **kwargs):
    fields = CONTA_FIELDS if sender is ConfiguracaoConta else CONTEXT_FIELDS
    old_values = getattr(instance, "_old_values", {})
    ip, agent, fonte = get_request_info()
    changes: dict[str, object] = {}
    for field in fields:
        old = old_values.get(field)
        new = getattr(instance, field)
        if created or old != new:
            ConfiguracaoContaLog.objects.create(
                user=instance.user,
                campo=field,
                valor_antigo=old,
                valor_novo=new,
                ip=ip,
                user_agent=agent,
                fonte=fonte,
            )
            changes[field] = new
    if changes:
        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(
                f"configuracoes_{instance.user.id}",
                {"type": "configuracoes.message", "data": changes},
            )
        except Exception as exc:  # pragma: no cover - channels layer failure
            sentry_sdk.capture_exception(exc)
    if sender is ConfiguracaoConta:
        cache.set(CACHE_KEY.format(id=instance.user_id), instance)
    else:
        cache.delete(
            CONTEXT_CACHE_KEY.format(
                user_id=instance.user_id,
                escopo_tipo=instance.escopo_tipo,
                escopo_id=instance.escopo_id,
            )
        )

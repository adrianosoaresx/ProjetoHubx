from __future__ import annotations

from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from .models import Empresa
from .services import LOG_FIELDS, registrar_alteracoes


@receiver(pre_save, sender=Empresa)
def _store_old_data(sender, instance, **kwargs):
    if instance.pk and sender.objects.filter(pk=instance.pk).exists():
        old = sender.objects.get(pk=instance.pk)
        instance._old_data = {f: getattr(old, f) for f in LOG_FIELDS if f != "tags"}
        instance._old_tags = list(old.tags.values_list("nome", flat=True))
    else:
        instance._old_data = {f: None for f in LOG_FIELDS if f != "tags"}
        instance._old_tags = []


@receiver(post_save, sender=Empresa)
def _log_changes(sender, instance, created, **kwargs):
    if created:
        return
    old_data = getattr(instance, "_old_data", {})
    old_data["tags"] = getattr(instance, "_old_tags", [])
    registrar_alteracoes(instance.usuario, instance, old_data)


@receiver(m2m_changed, sender=Empresa.tags.through)
def _log_tags(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove"}:
        old_tags = getattr(instance, "_old_tags", [])
        old_data = {"tags": old_tags}
        registrar_alteracoes(instance.usuario, instance, old_data)
        instance._old_tags = list(instance.tags.values_list("nome", flat=True))

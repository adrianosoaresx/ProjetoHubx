from __future__ import annotations

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Evento, InscricaoEvento
from .tasks import promover_lista_espera


@receiver(pre_save, sender=InscricaoEvento)
def _inscricao_store_old(sender, instance, **kwargs):
    if instance.pk:
        old = sender.all_objects.filter(pk=instance.pk).values("status", "deleted").first()
        if old:
            instance._old_status = old["status"]
            instance._old_deleted = old["deleted"]
            return
    instance._old_status = None
    instance._old_deleted = False


@receiver(post_save, sender=InscricaoEvento)
def _inscricao_trigger_waitlist(sender, instance, created, **kwargs):
    if created:
        return
    old_status = getattr(instance, "_old_status", None)
    old_deleted = getattr(instance, "_old_deleted", False)
    if (instance.status == "cancelada" and old_status != "cancelada") or (instance.deleted and not old_deleted):
        promover_lista_espera.delay(str(instance.evento_id))


@receiver(pre_save, sender=Evento)
def _evento_store_old(sender, instance, **kwargs):
    if instance.pk:
        old = sender.all_objects.filter(pk=instance.pk).values("participantes_maximo").first()
        if old:
            instance._old_participantes_maximo = old["participantes_maximo"]
            return
    instance._old_participantes_maximo = None


@receiver(post_save, sender=Evento)
def _evento_trigger_waitlist(sender, instance, created, **kwargs):
    if created:
        return
    old = getattr(instance, "_old_participantes_maximo", None)
    new = instance.participantes_maximo
    if new is not None and (old is None or new > old):
        promover_lista_espera.delay(str(instance.pk))

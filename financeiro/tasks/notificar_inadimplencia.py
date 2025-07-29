from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from ..models import LancamentoFinanceiro


@shared_task
def notificar_inadimplencia() -> None:
    pendentes = (
        LancamentoFinanceiro.objects.select_related("conta_associado__user")
        .filter(status=LancamentoFinanceiro.Status.PENDENTE, data_vencimento__lt=timezone.now())
        .filter(
            # notificados recentemente serão ignorados
            ultima_notificacao__isnull=True
        )
    )
    for lanc in pendentes:
        user = lanc.conta_associado.user if lanc.conta_associado else None
        # Placeholder de envio
        if user:
            print(f"Aviso de inadimplência para {user.email} - {lanc.valor}")
        lanc.ultima_notificacao = timezone.now()
        lanc.save(update_fields=["ultima_notificacao"])

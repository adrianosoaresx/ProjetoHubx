from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from ..models import LancamentoFinanceiro

logger = logging.getLogger(__name__)


@shared_task
def notificar_inadimplencia() -> None:
    """Envia avisos de inadimplência aos associados."""
    logger.info("Verificando inadimplentes")
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
            logger.info("Aviso de inadimplência para %s", user.email)
        lanc.ultima_notificacao = timezone.now()
        lanc.save(update_fields=["ultima_notificacao"])
    logger.info("Processo de notificação finalizado")
    # metrics.notificacoes_total.inc()  # Exemplo de métrica Prometheus

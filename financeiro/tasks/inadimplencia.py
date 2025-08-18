"""Tarefas relacionadas à inadimplência."""

from __future__ import annotations

import logging

from celery import shared_task  # type: ignore
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from ..models import FinanceiroTaskLog, LancamentoFinanceiro
from ..services import metrics
from ..services.notificacoes import enviar_aviso_vencimento, enviar_inadimplencia

logger = logging.getLogger(__name__)


@shared_task
def notificar_inadimplencia() -> None:
    """Envia notificações de inadimplência ou aviso de vencimento."""

    logger.info("Verificando inadimplentes")
    inicio = timezone.now()
    limite = inicio - timezone.timedelta(days=7)
    aviso_limite = inicio + timezone.timedelta(days=3)

    pendentes = (
        LancamentoFinanceiro.objects.select_related(
            "conta_associado__user",
            "centro_custo__nucleo",
            "centro_custo__organizacao",
        )
        .filter(status=LancamentoFinanceiro.Status.PENDENTE)
        .filter(Q(data_vencimento__lt=inicio) | Q(data_vencimento__lte=aviso_limite))
        .filter(
            Q(ultima_notificacao__isnull=True)
            | Q(ultima_notificacao__lt=limite)
            | Q(ultima_notificacao__lt=F("data_vencimento"))
        )
    )

    total = 0
    status = "sucesso"
    detalhes = ""
    try:
        for lancamento in pendentes:
            user = lancamento.conta_associado.user if lancamento.conta_associado else None
            if user:
                try:  # pragma: no branch - falhas de integração não são cobertas
                    if lancamento.data_vencimento and lancamento.data_vencimento > inicio:
                        enviar_aviso_vencimento(user, lancamento)
                        logger.info("Aviso de vencimento para %s", user.email)
                    else:
                        enviar_inadimplencia(user, lancamento)
                        logger.info("Aviso de inadimplência para %s", user.email)
                except Exception as exc:  # pragma: no cover - integração externa
                    logger.error("Falha ao enviar inadimplência: %s", exc)
            with transaction.atomic():
                lancamento.ultima_notificacao = timezone.now()
                lancamento.save(update_fields=["ultima_notificacao"])
            total += 1
    except Exception as exc:  # pragma: no cover - erro inesperado
        status = "erro"
        detalhes = str(exc)
        logger.exception("Erro ao processar inadimplências: %s", exc)
        raise
    finally:
        elapsed = (timezone.now() - inicio).total_seconds()
        logger.info(
            "Notificação de inadimplência finalizada: %s registros em %.2fs",
            total,
            elapsed,
        )
        metrics.notificacoes_total.inc(total)
        metrics.notificacoes_inadimplencia_total.inc(total)
        FinanceiroTaskLog.objects.create(
            nome_tarefa="notificar_inadimplencia",
            status=status,
            detalhes=detalhes or f"{total} notificações",
        )

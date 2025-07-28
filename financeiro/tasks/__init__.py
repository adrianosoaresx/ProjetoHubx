from __future__ import annotations

import random
from decimal import Decimal

from celery import shared_task
from django.utils import timezone

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro


@shared_task
def gerar_cobrancas_mensais() -> None:
    """Gera cobranças mensais fictícias para todos os associados."""
    associados = ContaAssociado.objects.all()
    centros = CentroCusto.objects.all()
    if not centros:
        return
    for conta in associados:
        centro = random.choice(centros)
        LancamentoFinanceiro.objects.create(
            centro_custo=centro,
            conta_associado=conta,
            tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
            valor=Decimal("50"),
            data_lancamento=timezone.now(),
            status=LancamentoFinanceiro.Status.PENDENTE,
            descricao="Cobrança mensal",
        )

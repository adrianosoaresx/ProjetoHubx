from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Sequence

from django.db.models import Case, DecimalField, Sum, Value, When
from django.db.models.functions import TruncMonth

from ..models import CentroCusto, LancamentoFinanceiro
from ..reporting import saldos_carteiras_por_centro


def _base_queryset(
    centro: str | Sequence[str] | None,
    nucleo: str | None,
    inicio: datetime | None,
    fim: datetime | None,
) -> Iterable[LancamentoFinanceiro]:
    """Retorna queryset filtrado para geração de relatórios."""
    qs = LancamentoFinanceiro.objects.select_related("centro_custo").prefetch_related("conta_associado").all()

    if centro:
        if isinstance(centro, str):
            qs = qs.filter(centro_custo_id=centro)
        else:
            qs = qs.filter(centro_custo_id__in=list(centro))
    elif nucleo:
        qs = qs.filter(centro_custo__nucleo_id=nucleo)

    if inicio:
        qs = qs.filter(data_lancamento__gte=inicio)
    if fim:
        qs = qs.filter(data_lancamento__lt=fim)
    return qs


def gerar_relatorio(
    *,
    centro: str | Sequence[str] | None = None,
    nucleo: str | None = None,
    periodo_inicial: datetime | None = None,
    periodo_final: datetime | None = None,
    tipo: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Computa séries temporais e consolida saldos."""
    qs = _base_queryset(centro, nucleo, periodo_inicial, periodo_final)
    if tipo == "receitas":
        qs = qs.filter(valor__gt=0)
    elif tipo == "despesas":
        qs = qs.filter(valor__lt=0)
    if status:
        qs = qs.filter(status=status)

    valores = (
        qs.annotate(mes=TruncMonth("data_lancamento"))
        .values("mes")
        .annotate(
            receitas=Sum(
                Case(
                    When(valor__gt=0, then="valor"),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            despesas=Sum(
                Case(
                    When(valor__lt=0, then="valor"),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by("mes")
    )

    saldo_acumulado = Decimal("0")
    serie: list[dict[str, Any]] = []
    for item in valores:
        receitas = item["receitas"] or Decimal("0")
        despesas = item["despesas"] or Decimal("0")
        saldo_acumulado += receitas + despesas
        serie.append(
            {
                "mes": item["mes"].strftime("%Y-%m"),
                "receitas": float(receitas),
                "despesas": float(abs(despesas)),
                "saldo": float(saldo_acumulado),
            }
        )

    saldos_centros = saldos_carteiras_por_centro(centro=centro, nucleo=nucleo)

    saldo_atual = sum(saldos_centros.values(), Decimal("0"))

    centros_meta: dict[str, dict[str, Any]] = {}
    if saldos_centros:
        centros_meta = {
            str(item["id"]): {"nome": item["nome"], "tipo": item["tipo"]}
            for item in CentroCusto.objects.filter(pk__in=list(saldos_centros.keys())).values("id", "nome", "tipo")
        }
    classificacao_centros = [
        {
            "id": centro_id,
            "nome": centros_meta.get(centro_id, {}).get("nome"),
            "tipo": centros_meta.get(centro_id, {}).get("tipo"),
            "saldo": float(valor),
        }
        for centro_id, valor in sorted(
            saldos_centros.items(),
            key=lambda item: centros_meta.get(item[0], {}).get("nome") or "",
        )
    ]

    return {
        "saldo_atual": float(saldo_atual),
        "serie": serie,
        "saldos_por_centro": {cid: float(valor) for cid, valor in saldos_centros.items()},
        "classificacao_centros": classificacao_centros,
    }

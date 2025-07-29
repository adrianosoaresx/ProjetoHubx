from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Sequence

from django.db.models import Case, DecimalField, Sum, Value, When
from django.db.models.functions import TruncMonth

from ..models import CentroCusto, LancamentoFinanceiro


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
) -> dict[str, Any]:
    """Computa séries temporais e dados de inadimplência."""
    qs = _base_queryset(centro, nucleo, periodo_inicial, periodo_final)

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

    saldo_atual: Decimal
    if centro:
        if isinstance(centro, str):
            saldo_atual = CentroCusto.objects.filter(pk=centro).aggregate(total=Sum("saldo"))["total"] or Decimal("0")
        else:
            saldo_atual = CentroCusto.objects.filter(pk__in=list(centro)).aggregate(total=Sum("saldo"))[
                "total"
            ] or Decimal("0")
    elif nucleo:
        saldo_atual = CentroCusto.objects.filter(nucleo_id=nucleo).aggregate(total=Sum("saldo"))["total"] or Decimal(
            "0"
        )
    else:
        saldo_atual = CentroCusto.objects.aggregate(total=Sum("saldo"))["total"] or Decimal("0")

    pendentes = qs.filter(status=LancamentoFinanceiro.Status.PENDENTE)
    quitadas = qs.filter(
        status=LancamentoFinanceiro.Status.PAGO,
        ultima_notificacao__isnull=False,
    )

    def _serie_inadimplencia(qs_in: Iterable[LancamentoFinanceiro], key: str) -> dict[str, dict[str, float]]:
        data: dict[str, dict[str, float]] = defaultdict(lambda: {"pendentes": 0.0, "quitadas": 0.0})
        res = (
            qs_in.annotate(mes=TruncMonth("data_lancamento")).values("mes").annotate(valor=Sum("valor")).order_by("mes")
        )
        for item in res:
            mes = item["mes"].strftime("%Y-%m")
            data[mes][key] = float(item["valor"] or 0)
        return data

    dados_pend = _serie_inadimplencia(pendentes, "pendentes")
    dados_quit = _serie_inadimplencia(quitadas, "quitadas")

    meses = sorted(set(dados_pend.keys()) | set(dados_quit.keys()))
    inadimplencia: list[dict[str, Any]] = []
    for mes in meses:
        item = {"mes": mes, **dados_pend.get(mes, {}), **dados_quit.get(mes, {})}
        item.setdefault("pendentes", 0.0)
        item.setdefault("quitadas", 0.0)
        inadimplencia.append(item)

    return {
        "saldo_atual": float(saldo_atual),
        "serie": serie,
        "inadimplencia": inadimplencia,
    }

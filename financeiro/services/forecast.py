from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Case, DecimalField, Sum, Value, When
from django.db.models.functions import TruncMonth
from django.utils import timezone

from ..models import LancamentoFinanceiro


# Mapeia o escopo informado para os filtros correspondentes no queryset
_SCOPES = {
    "organizacao": "centro_custo__organizacao_id",
    "nucleo": "centro_custo__nucleo_id",
    "centro": "centro_custo_id",
    "evento": "centro_custo__evento_id",
}


def _aggregated_queryset(escopo: str, id_ref: str):
    """Retorna um queryset agrupado por mês para o escopo informado."""
    if escopo not in _SCOPES:
        raise ValueError("escopo inválido")

    filtro = {_SCOPES[escopo]: id_ref}
    inicio = timezone.now() - timezone.timedelta(days=730)  # aprox. 24 meses
    qs = (
        LancamentoFinanceiro.objects.filter(data_lancamento__gte=inicio, **filtro)
        .annotate(mes=TruncMonth("data_lancamento"))
        .values("mes")
        .annotate(
            receita=Sum(
                Case(
                    When(valor__gt=0, then="valor"),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
            despesa=Sum(
                Case(
                    When(valor__lt=0, then="valor"),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            ),
        )
        .order_by("mes")
    )
    return list(qs)


def calcular_previsao(
    escopo: str,
    id_ref: str,
    periodos: int,
    crescimento_receita: float = 0,
    reducao_despesa: float = 0,
) -> dict[str, Any]:
    """Calcula previsão financeira com média móvel e sazonalidade simples."""

    historico_bruto = _aggregated_queryset(escopo, id_ref)
    historico: list[dict[str, Any]] = []
    saldo = Decimal("0")
    receitas_hist: list[Decimal] = []
    despesas_hist: list[Decimal] = []

    for item in historico_bruto:
        receita = item["receita"] or Decimal("0")
        despesa = abs(item["despesa"] or Decimal("0"))
        saldo += receita - despesa
        historico.append(
            {
                "mes": item["mes"].strftime("%Y-%m"),
                "receita": float(receita),
                "despesa": float(despesa),
                "saldo": float(saldo),
                "intervalo_conf": None,
            }
        )
        receitas_hist.append(receita)
        despesas_hist.append(despesa)

    # calcula desvio padrão para intervalo de confiança simples
    desv = Decimal("0")
    if historico:
        saldos = [Decimal(str(h["saldo"])) for h in historico]
        if len(saldos) > 1:
            media = sum(saldos) / len(saldos)
            variancia = sum((s - media) ** 2 for s in saldos) / (len(saldos) - 1)
            desv = variancia.sqrt() if hasattr(variancia, "sqrt") else Decimal(variancia) ** Decimal("0.5")
        for h in historico:
            h["intervalo_conf"] = [float(Decimal(str(h["saldo"])) - desv), float(Decimal(str(h["saldo"])) + desv)]

    previsao: list[dict[str, Any]] = []
    n_hist = len(historico)

    if n_hist >= 6:
        # média móvel 3 meses
        saz_receita: dict[int, float] = defaultdict(lambda: 1.0)
        saz_despesa: dict[int, float] = defaultdict(lambda: 1.0)
        if n_hist >= 12:
            media_rec = float(sum(receitas_hist) / n_hist) if n_hist else 0
            media_desp = float(sum(despesas_hist) / n_hist) if n_hist else 0
            by_month_rec: dict[int, list[Decimal]] = defaultdict(list)
            by_month_desp: dict[int, list[Decimal]] = defaultdict(list)
            for h in historico_bruto:
                m = h["mes"].month
                by_month_rec[m].append(h["receita"] or Decimal("0"))
                by_month_desp[m].append(abs(h["despesa"] or Decimal("0")))
            for m in range(1, 13):
                if by_month_rec[m] and media_rec:
                    saz_receita[m] = float(sum(by_month_rec[m]) / len(by_month_rec[m])) / media_rec
                if by_month_desp[m] and media_desp:
                    saz_despesa[m] = float(sum(by_month_desp[m]) / len(by_month_desp[m])) / media_desp

        ult_mes = datetime.strptime(historico[-1]["mes"], "%Y-%m")
        rec_vals = receitas_hist[-3:]
        desp_vals = despesas_hist[-3:]
        for i in range(1, periodos + 1):
            ano = ult_mes.year + (ult_mes.month + i - 1) // 12
            mes = (ult_mes.month + i - 1) % 12 + 1
            base_rec = float(sum(rec_vals[-3:]) / min(len(rec_vals), 3))
            base_desp = float(sum(desp_vals[-3:]) / min(len(desp_vals), 3))
            base_rec *= saz_receita[mes]
            base_desp *= saz_despesa[mes]
            base_rec *= 1 + (crescimento_receita / 100)
            base_desp *= 1 - (reducao_despesa / 100)
            saldo += Decimal(base_rec) - Decimal(base_desp)
            rec_vals.append(Decimal(base_rec))
            desp_vals.append(Decimal(base_desp))
            previsao.append(
                {
                    "mes": f"{ano:04d}-{mes:02d}",
                    "receita": float(round(base_rec, 2)),
                    "despesa": float(round(base_desp, 2)),
                    "saldo": float(round(saldo, 2)),
                    "intervalo_conf": [
                        float(saldo - desv),
                        float(saldo + desv),
                    ],
                }
            )
    else:
        # fallback média simples
        rec_media = float(sum(receitas_hist) / n_hist) if n_hist else 0
        desp_media = float(sum(despesas_hist) / n_hist) if n_hist else 0
        ult_mes = historico[-1]["mes"] if historico else timezone.now().strftime("%Y-%m")
        ult_dt = datetime.strptime(ult_mes, "%Y-%m")
        for i in range(1, periodos + 1):
            ano = ult_dt.year + (ult_dt.month + i - 1) // 12
            mes = (ult_dt.month + i - 1) % 12 + 1
            rec_val = rec_media * (1 + crescimento_receita / 100)
            desp_val = desp_media * (1 - reducao_despesa / 100)
            saldo += Decimal(rec_val) - Decimal(desp_val)
            previsao.append(
                {
                    "mes": f"{ano:04d}-{mes:02d}",
                    "receita": float(round(rec_val, 2)),
                    "despesa": float(round(desp_val, 2)),
                    "saldo": float(round(saldo, 2)),
                    "intervalo_conf": [
                        float(saldo - desv),
                        float(saldo + desv),
                    ],
                }
            )

    return {"historico": historico, "previsao": previsao}

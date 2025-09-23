"""Funções auxiliares para obtenção de saldos de carteiras."""

from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from typing import Sequence

from django.db.models import Sum
from django.db.models.functions import Coalesce

from ..models import Carteira, LancamentoFinanceiro

SaldoCarteiraMapa = dict[str, Decimal]

ZERO = Decimal("0")


def _normalize_centros(centro: str | Sequence[str] | None) -> list[str]:
    """Normaliza parâmetros de centros para lista de identificadores."""

    if centro is None:
        return []
    if isinstance(centro, str):
        return [centro]
    return [str(item) for item in centro]


def _aplicar_filtros_carteira(
    centro: str | Sequence[str] | None,
    *,
    nucleo: str | None = None,
):
    centros = _normalize_centros(centro)
    qs = Carteira.objects.filter(centro_custo__isnull=False)
    if centros:
        qs = qs.filter(centro_custo_id__in=centros)
    elif nucleo:
        qs = qs.filter(centro_custo__nucleo_id=nucleo)
    return qs, centros


def _aplicar_filtros_lancamento(
    centro: str | Sequence[str] | None,
    *,
    nucleo: str | None = None,
):
    centros = _normalize_centros(centro)
    qs = LancamentoFinanceiro.objects.filter(status=LancamentoFinanceiro.Status.PAGO)
    if centros:
        qs = qs.filter(centro_custo_id__in=centros)
    elif nucleo:
        qs = qs.filter(centro_custo__nucleo_id=nucleo)
    return qs, centros


def _com_defaults(dados: SaldoCarteiraMapa, centros: list[str]) -> SaldoCarteiraMapa:
    """Assegura que todos os centros solicitados apareçam no resultado."""

    if centros:
        for centro_id in centros:
            dados.setdefault(str(centro_id), ZERO)
    return dados


def saldos_materializados_por_centro(
    *,
    centro: str | Sequence[str] | None = None,
    nucleo: str | None = None,
) -> SaldoCarteiraMapa:
    """Retorna saldos somados a partir do campo materializado ``Carteira.saldo``."""

    qs, _centros = _aplicar_filtros_carteira(centro, nucleo=nucleo)
    agregados = (
        qs.values_list("centro_custo_id")
        .annotate(total=Coalesce(Sum("saldo"), ZERO))
        .order_by()
    )
    resultado: SaldoCarteiraMapa = OrderedDict()
    for centro_id, total in agregados:
        if centro_id is None:
            continue
        resultado[str(centro_id)] = total
    return resultado


def saldos_lancamentos_por_centro(
    *,
    centro: str | Sequence[str] | None = None,
    nucleo: str | None = None,
) -> SaldoCarteiraMapa:
    """Retorna saldos calculados via lançamentos pagos."""

    qs, _centros = _aplicar_filtros_lancamento(centro, nucleo=nucleo)
    agregados = (
        qs.values_list("centro_custo_id")
        .annotate(total=Coalesce(Sum("valor"), ZERO))
        .order_by()
    )
    resultado: SaldoCarteiraMapa = OrderedDict()
    for centro_id, total in agregados:
        if centro_id is None:
            continue
        resultado[str(centro_id)] = total
    return resultado


def saldos_carteiras_por_centro(
    *,
    centro: str | Sequence[str] | None = None,
    nucleo: str | None = None,
    prefer_materializado: bool = True,
    fallback_to_lancamentos: bool = True,
) -> SaldoCarteiraMapa:
    """Obtém saldos consolidados por centro de custo considerando carteiras."""

    centros_alvo = _normalize_centros(centro)
    if prefer_materializado:
        materializado = saldos_materializados_por_centro(centro=centro, nucleo=nucleo)
        if not fallback_to_lancamentos:
            return _com_defaults(materializado, centros_alvo)
        if materializado:
            if centros_alvo:
                faltantes = {cid for cid in centros_alvo if cid not in materializado}
                if faltantes:
                    agregados = saldos_lancamentos_por_centro(centro=centro, nucleo=nucleo)
                    for chave in faltantes:
                        materializado[chave] = agregados.get(chave, ZERO)
                return _com_defaults(materializado, centros_alvo)
            agregados = saldos_lancamentos_por_centro(centro=centro, nucleo=nucleo)
            for chave, valor in agregados.items():
                materializado.setdefault(chave, valor)
            return _com_defaults(materializado, centros_alvo)
        agregados = saldos_lancamentos_por_centro(centro=centro, nucleo=nucleo)
        return _com_defaults(agregados, centros_alvo)
    agregados = saldos_lancamentos_por_centro(centro=centro, nucleo=nucleo)
    return _com_defaults(agregados, centros_alvo)

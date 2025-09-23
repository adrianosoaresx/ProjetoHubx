"""Utilitários para ajuste de saldos em carteiras e registros legados."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from django.conf import settings
from django.db.models import F

from ..models import Carteira, CentroCusto, ContaAssociado, LancamentoFinanceiro

DecimalLike = Decimal | float | int | str
_SENTINEL = object()


def _to_decimal(valor: DecimalLike | None) -> Optional[Decimal]:
    """Converte ``valor`` para :class:`~decimal.Decimal` quando não nulo."""

    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return valor
    return Decimal(valor)


def creditar(valor: DecimalLike) -> Decimal:
    """Retorna o valor positivo para crédito em uma carteira."""

    result = _to_decimal(valor)
    if result is None:
        return Decimal("0")
    return result


def debitar(valor: DecimalLike) -> Decimal:
    """Retorna o valor negativo (débito) respeitando o sinal original."""

    result = _to_decimal(valor)
    if result is None:
        return Decimal("0")
    return -result if result >= 0 else result


def _cache_get(cache: Dict[str, Dict[Any, Optional[Carteira]]] | None, key: str, obj_id: Any):
    if cache is None:
        return _SENTINEL
    bucket = cache.setdefault(key, {})
    return bucket.get(obj_id, _SENTINEL)


def _cache_set(
    cache: Dict[str, Dict[Any, Optional[Carteira]]] | None,
    key: str,
    obj_id: Any,
    value: Optional[Carteira],
) -> None:
    if cache is None:
        return
    bucket = cache.setdefault(key, {})
    bucket[obj_id] = value


def carteira_operacional_centro(centro: CentroCusto | None) -> Optional[Carteira]:
    """Obtém a carteira operacional vinculada ao centro de custo."""

    if not centro:
        return None
    cached = getattr(centro, "_carteira_operacional_cache", _SENTINEL)
    if cached is not _SENTINEL:
        return cached  # type: ignore[return-value]
    carteira = (
        centro.carteiras.filter(tipo=Carteira.Tipo.OPERACIONAL)
        .only("id", "centro_custo_id", "conta_associado_id")
        .order_by("created_at")
        .first()
    )
    setattr(centro, "_carteira_operacional_cache", carteira)
    return carteira


def carteira_operacional_conta(conta: ContaAssociado | None) -> Optional[Carteira]:
    """Obtém a carteira operacional vinculada à conta do associado."""

    if not conta:
        return None
    cached = getattr(conta, "_carteira_operacional_cache", _SENTINEL)
    if cached is not _SENTINEL:
        return cached  # type: ignore[return-value]
    carteira = (
        conta.carteiras.filter(tipo=Carteira.Tipo.OPERACIONAL)
        .only("id", "centro_custo_id", "conta_associado_id")
        .order_by("created_at")
        .first()
    )
    setattr(conta, "_carteira_operacional_cache", carteira)
    return carteira


def atribuir_carteiras_padrao(
    dados: dict[str, Any],
    *,
    cache: Dict[str, Dict[Any, Optional[Carteira]]] | None = None,
) -> None:
    """Garante que os dados contenham carteiras operacionais padrão."""

    centro = dados.get("centro_custo")
    if centro and not dados.get("carteira"):
        cached = _cache_get(cache, "centro", centro.id)
        if cached is _SENTINEL:
            cached = carteira_operacional_centro(centro)
            _cache_set(cache, "centro", centro.id, cached)
        if cached:
            dados["carteira"] = cached

    conta = dados.get("conta_associado")
    if conta and not dados.get("carteira_contraparte"):
        cached = _cache_get(cache, "conta", conta.id)
        if cached is _SENTINEL:
            cached = carteira_operacional_conta(conta)
            _cache_set(cache, "conta", conta.id, cached)
        if cached:
            dados["carteira_contraparte"] = cached


def aplicar_ajustes(
    *,
    centro_custo: CentroCusto | None,
    carteira: Carteira | None,
    centro_delta: DecimalLike | None,
    conta_associado: ContaAssociado | None = None,
    carteira_contraparte: Carteira | None = None,
    contraparte_delta: DecimalLike | None = None,
) -> None:
    """Aplica ajustes nas carteiras e opcionalmente nos modelos legados."""

    centro_delta_dec = _to_decimal(centro_delta)
    contraparte_delta_dec = _to_decimal(contraparte_delta)

    if centro_delta_dec and centro_delta_dec != 0:
        carteira_ref = carteira or carteira_operacional_centro(centro_custo)
        if carteira_ref:
            Carteira.objects.filter(pk=carteira_ref.pk).update(saldo=F("saldo") + centro_delta_dec)
        if centro_custo and not settings.FINANCEIRO_SOMENTE_CARTEIRA:
            CentroCusto.objects.filter(pk=centro_custo.pk).update(saldo=F("saldo") + centro_delta_dec)

    if contraparte_delta_dec and contraparte_delta_dec != 0:
        carteira_ref = carteira_contraparte or carteira_operacional_conta(conta_associado)
        if carteira_ref:
            Carteira.objects.filter(pk=carteira_ref.pk).update(saldo=F("saldo") + contraparte_delta_dec)
        if conta_associado and not settings.FINANCEIRO_SOMENTE_CARTEIRA:
            ContaAssociado.objects.filter(pk=conta_associado.pk).update(
                saldo=F("saldo") + contraparte_delta_dec
            )


def vincular_carteiras_lancamento(lancamento: LancamentoFinanceiro) -> None:
    """Garante que o lançamento possua carteiras associadas."""

    campos: list[str] = []
    if not lancamento.carteira_id:
        carteira = carteira_operacional_centro(getattr(lancamento, "centro_custo", None))
        if carteira:
            lancamento.carteira = carteira
            campos.append("carteira")
    if not lancamento.carteira_contraparte_id and getattr(lancamento, "conta_associado_id", None):
        conta = getattr(lancamento, "conta_associado", None)
        carteira_contra = carteira_operacional_conta(conta)
        if carteira_contra:
            lancamento.carteira_contraparte = carteira_contra
            campos.append("carteira_contraparte")
    if campos:
        lancamento.save(update_fields=campos)

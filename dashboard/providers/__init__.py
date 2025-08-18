from __future__ import annotations

from typing import Any, Callable

from accounts.models import User, UserType
from agenda.models import InscricaoEvento
from financeiro.models import LancamentoFinanceiro

ProviderFn = Callable[[User, dict[str, Any]], dict[str, float]]

REGISTRY: dict[str, ProviderFn] = {}


def provider(name: str) -> Callable[[ProviderFn], ProviderFn]:
    """Decorator to register a metric provider."""

    def wrapper(func: ProviderFn) -> ProviderFn:
        REGISTRY[name] = func
        return func

    return wrapper


@provider("contar_usuarios")
def contar_usuarios(user: User, params: dict[str, Any]) -> dict[str, float]:
    """Conta usuários visíveis ao usuário atual."""
    qs = User.objects.all()
    if user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        qs = qs.filter(organizacao=user.organizacao)
    total = qs.count()
    return {"total": float(total), "crescimento": 0.0}


@provider("contar_inscricoes_confirmadas")
def contar_inscricoes_confirmadas(user: User, params: dict[str, Any]) -> dict[str, float]:
    qs = InscricaoEvento.objects.filter(status="confirmada")
    if user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        qs = qs.filter(evento__organizacao=user.organizacao)
    return {"total": float(qs.count()), "crescimento": 0.0}


@provider("contar_lancamentos_pendentes")
def contar_lancamentos_pendentes(user: User, params: dict[str, Any]) -> dict[str, float]:
    qs = LancamentoFinanceiro.objects.filter(status=LancamentoFinanceiro.Status.PENDENTE)
    if user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        qs = qs.filter(centro_custo__organizacao=user.organizacao)
    return {"total": float(qs.count()), "crescimento": 0.0}

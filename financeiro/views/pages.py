from __future__ import annotations

import uuid

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from accounts.models import UserType
from eventos.models import Evento

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro


def _is_financeiro_or_admin(user) -> bool:
    permitido = {UserType.ADMIN, UserType.FINANCEIRO}
    return user.is_authenticated and user.user_type in permitido


def _is_associado(user) -> bool:
    return user.is_authenticated and user.user_type == UserType.ASSOCIADO


def _require_financeiro_or_admin(user) -> None:
    if not _is_financeiro_or_admin(user):
        raise PermissionDenied


def _require_associado(user) -> None:
    if not _is_associado(user):
        raise PermissionDenied


@login_required
def importar_pagamentos_view(request):
    _require_financeiro_or_admin(request.user)
    context = {"legacy_warning": ContaAssociado.LEGACY_MESSAGE}
    return render(request, "financeiro/importar_pagamentos.html", context)


@login_required
def relatorios_view(request):
    _require_financeiro_or_admin(request.user)
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
        "legacy_warning": ContaAssociado.LEGACY_MESSAGE,
    }
    return render(request, "financeiro/relatorios.html", context)


@login_required
def importacoes_list_view(request):
    _require_financeiro_or_admin(request.user)
    """Lista de importações de pagamentos."""
    return render(request, "financeiro/importacoes_list.html")


@login_required
def lancamentos_list_view(request):
    _require_financeiro_or_admin(request.user)
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
        "legacy_warning": ContaAssociado.LEGACY_MESSAGE,
    }
    return render(request, "financeiro/lancamentos_list.html", context)


@login_required
def lancamento_ajuste_modal_view(request, pk: uuid.UUID):
    _require_financeiro_or_admin(request.user)
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    return render(request, "financeiro/lancamento_ajuste_modal.html", {"lancamento": lancamento})


@login_required
def repasses_view(request):
    _require_financeiro_or_admin(request.user)
    eventos = Evento.objects.all()
    return render(
        request,
        "financeiro/repasses.html",
        {"eventos": eventos, "legacy_warning": ContaAssociado.LEGACY_MESSAGE},
    )


@login_required
def aportes_form_view(request):
    _require_associado(request.user)
    centros = CentroCusto.objects.all()
    return render(request, "financeiro/aportes_form.html", {"centros": centros})


@login_required
def extrato_view(request):
    _require_associado(request.user)
    """Lista os lançamentos financeiros do associado."""
    lancamentos = (
        LancamentoFinanceiro.objects.filter(
            Q(conta_associado__user=request.user)
            | Q(carteira_contraparte__conta_associado__user=request.user)
        )
        .select_related(
            "centro_custo",
            "carteira_contraparte__conta_associado__user",
            "conta_associado__user",
        )
        .order_by("-data_lancamento")
    )
    context = {
        "lancamentos": lancamentos,
        "legacy_warning": ContaAssociado.LEGACY_MESSAGE,
    }
    return render(request, "financeiro/extrato.html", context)

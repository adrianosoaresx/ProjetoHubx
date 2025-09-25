from __future__ import annotations

import uuid

from django.contrib.auth.decorators import login_required, user_passes_test
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


@login_required
@user_passes_test(_is_financeiro_or_admin)
def importar_pagamentos_view(request):
    context = {"legacy_warning": ContaAssociado.LEGACY_MESSAGE}
    return render(request, "financeiro/importar_pagamentos.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def relatorios_view(request):
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
        "legacy_warning": ContaAssociado.LEGACY_MESSAGE,
    }
    return render(request, "financeiro/relatorios.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def importacoes_list_view(request):
    """Lista de importações de pagamentos."""
    return render(request, "financeiro/importacoes_list.html")


@login_required
@user_passes_test(_is_financeiro_or_admin)
def lancamentos_list_view(request):
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
        "legacy_warning": ContaAssociado.LEGACY_MESSAGE,
    }
    return render(request, "financeiro/lancamentos_list.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def lancamento_ajuste_modal_view(request, pk: uuid.UUID):
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    return render(request, "financeiro/lancamento_ajuste_modal.html", {"lancamento": lancamento})


@login_required
@user_passes_test(_is_financeiro_or_admin)
def repasses_view(request):
    eventos = Evento.objects.all()
    return render(
        request,
        "financeiro/repasses.html",
        {"eventos": eventos, "legacy_warning": ContaAssociado.LEGACY_MESSAGE},
    )


@login_required
@user_passes_test(_is_associado)
def aportes_form_view(request):
    centros = CentroCusto.objects.all()
    return render(request, "financeiro/aportes_form.html", {"centros": centros})


@login_required
@user_passes_test(_is_associado)
def extrato_view(request):
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

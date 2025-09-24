from __future__ import annotations

import uuid

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from accounts.models import UserType
from eventos.models import Evento

from ..models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroLog,
    FinanceiroTaskLog,
    LancamentoFinanceiro,
)


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
def centros_list_view(request):
    limit = 20
    offset = int(request.GET.get("offset", 0))
    qs = (
        CentroCusto.objects.all()
        .select_related("organizacao", "nucleo", "evento")
        .annotate(
            saldo_total_carteiras=Coalesce(
                Sum(
                    "carteiras__saldo",
                    filter=Q(carteiras__deleted=False),
                ),
                Value(Decimal("0")),
            )
        )
    )
    total = qs.count()
    centros = qs[offset : offset + limit]
    next_offset = offset + limit if total > offset + limit else None
    prev_offset = offset - limit if offset - limit >= 0 else None
    context = {
        "centros": centros,
        "next": next_offset,
        "prev": prev_offset,
    }
    return render(request, "financeiro/centros_list.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def centro_form_view(request, pk: uuid.UUID | None = None):
    centro = get_object_or_404(CentroCusto, pk=pk) if pk is not None else None
    return render(request, "financeiro/centro_form.html", {"centro": centro})


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


def logs_list_view(request):
    User = get_user_model()
    context = {
        "acoes": FinanceiroLog.Acao.choices,
        "usuarios": User.objects.all(),
    }
    return render(request, "financeiro/logs_list.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def inadimplencias_view(request):
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
        "legacy_warning": ContaAssociado.LEGACY_MESSAGE,
    }
    return render(request, "financeiro/inadimplencias.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def task_logs_view(request):
    logs = FinanceiroTaskLog.objects.all()
    return render(request, "financeiro/task_logs.html", {"logs": logs})


@login_required
@user_passes_test(_is_financeiro_or_admin)
def task_log_detail_view(request, pk):
    log = get_object_or_404(FinanceiroTaskLog, pk=pk)
    return render(request, "financeiro/task_log_detail.html", {"log": log})


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

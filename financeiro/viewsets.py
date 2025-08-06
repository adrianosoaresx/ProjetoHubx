from __future__ import annotations

from calendar import monthrange
from datetime import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from .models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from .permissions import IsAssociadoReadOnly, IsCoordenador, IsFinanceiroOrAdmin
from .serializers import LancamentoFinanceiroSerializer
from .services.distribuicao import repassar_receita_ingresso
from .views import CentroCustoViewSet, FinanceiroViewSet


class LancamentoFinanceiroViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Listagem e atualização de lançamentos financeiros."""

    serializer_class = LancamentoFinanceiroSerializer

    def get_permissions(self):  # type: ignore[override]
        if self.action in {"partial_update"}:
            self.permission_classes = [IsAuthenticated, IsFinanceiroOrAdmin]
        else:
            self.permission_classes = [
                IsAuthenticated,
                IsFinanceiroOrAdmin | IsCoordenador | IsAssociadoReadOnly,
            ]
        return super().get_permissions()

    def get_queryset(self):  # type: ignore[override]
        qs = LancamentoFinanceiro.objects.select_related(
            "conta_associado__user",
            "centro_custo__nucleo",
            "centro_custo__organizacao",
        )
        user = self.request.user
        if user.user_type == UserType.COORDENADOR and user.nucleo_id:
            qs = qs.filter(centro_custo__nucleo_id=user.nucleo_id)
        elif user.user_type != UserType.ADMIN:
            qs = qs.filter(conta_associado__user=user)

        params = self.request.query_params
        if centro_id := params.get("centro"):
            qs = qs.filter(centro_custo_id=centro_id)
        if nucleo_id := params.get("nucleo"):
            qs = qs.filter(centro_custo__nucleo_id=nucleo_id)
        if status_param := params.get("status"):
            qs = qs.filter(status=status_param)

        def _parse(periodo: str | None) -> datetime | None:
            if not periodo or periodo.count("-") != 1:
                return None
            dt = parse_date(f"{periodo}-01")
            if dt:
                return datetime(dt.year, dt.month, 1)
            return None

        if (inicio := _parse(params.get("periodo_inicial"))):
            qs = qs.filter(data_lancamento__gte=inicio)
        if (fim := _parse(params.get("periodo_final"))):
            last_day = monthrange(fim.year, fim.month)[1]
            limite = datetime(fim.year, fim.month, last_day) + timezone.timedelta(days=1)
            qs = qs.filter(data_lancamento__lt=limite)
        return qs

    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        lancamento = self.get_object()
        novo_status = request.data.get("status")
        if novo_status not in {
            LancamentoFinanceiro.Status.PAGO,
            LancamentoFinanceiro.Status.CANCELADO,
        }:
            return Response({"detail": _("Status inválido")}, status=status.HTTP_400_BAD_REQUEST)
        if lancamento.status != LancamentoFinanceiro.Status.PENDENTE:
            return Response(
                {"detail": _("Apenas lançamentos pendentes podem ser alterados")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            lancamento.status = novo_status
            lancamento.save(update_fields=["status"])
            if novo_status == LancamentoFinanceiro.Status.PAGO:
                CentroCusto.objects.filter(pk=lancamento.centro_custo_id).update(
                    saldo=F("saldo") + lancamento.valor
                )
                if lancamento.conta_associado_id:
                    ContaAssociado.objects.filter(pk=lancamento.conta_associado_id).update(
                        saldo=F("saldo") + lancamento.valor
                    )
                if lancamento.tipo == LancamentoFinanceiro.Tipo.INGRESSO_EVENTO:
                    repassar_receita_ingresso(lancamento)

        serializer = self.get_serializer(lancamento)
        return Response(serializer.data)


__all__ = [
    "CentroCustoViewSet",
    "FinanceiroViewSet",
    "LancamentoFinanceiroViewSet",
]


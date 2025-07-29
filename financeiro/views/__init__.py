from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from ..models import CentroCusto, LancamentoFinanceiro
from ..permissions import IsAssociadoReadOnly, IsCoordenador, IsFinanceiroOrAdmin
from ..serializers import (
    AporteSerializer,
    CentroCustoSerializer,
    ImportarPagamentosConfirmacaoSerializer,
    ImportarPagamentosPreviewSerializer,
)
from ..services.cobrancas import _nucleos_do_usuario
from ..services.importacao import ImportadorPagamentos
from ..services.relatorios import gerar_relatorio
from ..tasks.importar_pagamentos import importar_pagamentos_async


class AportePermission(IsAuthenticated):
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not super().has_permission(request, view):
            return False
        tipo = request.data.get("tipo", LancamentoFinanceiro.Tipo.APORTE_INTERNO)
        if tipo == LancamentoFinanceiro.Tipo.APORTE_INTERNO:
            return request.user.user_type in {UserType.ADMIN, UserType.ROOT}
        return True


class CentroCustoViewSet(viewsets.ModelViewSet):
    """CRUD dos centros de custo."""

    queryset = CentroCusto.objects.all()
    serializer_class = CentroCustoSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.permission_classes = [IsAuthenticated, IsFinanceiroOrAdmin]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset().select_related("organizacao", "nucleo", "evento")
        user = self.request.user
        if user.user_type == UserType.COORDENADOR and user.nucleo_id:
            qs = qs.filter(nucleo_id=user.nucleo_id)
        return qs


class FinanceiroViewSet(viewsets.ViewSet):
    """Endpoints auxiliares do módulo financeiro."""

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in {"importar_pagamentos", "confirmar_importacao", "aportes"}:
            self.permission_classes = [IsAuthenticated, IsFinanceiroOrAdmin]
        elif self.action == "relatorios":
            self.permission_classes = [IsAuthenticated, IsFinanceiroOrAdmin | IsCoordenador]
        elif self.action == "inadimplencias":
            self.permission_classes = [IsAuthenticated, IsFinanceiroOrAdmin | IsCoordenador | IsAssociadoReadOnly]
        return super().get_permissions()

    def _lancamentos_base(self):
        qs = LancamentoFinanceiro.objects.select_related(
            "centro_custo__nucleo",
            "centro_custo__organizacao",
            "conta_associado__user",
        )
        user = self.request.user
        if user.user_type == UserType.COORDENADOR and user.nucleo_id:
            qs = qs.filter(centro_custo__nucleo_id=user.nucleo_id)
        elif user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            qs = qs.filter(conta_associado__user=user)
        return qs

    @action(detail=False, methods=["post"], url_path="importar-pagamentos")
    def importar_pagamentos(self, request):
        serializer = ImportarPagamentosPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data["file"]
        uid = uuid.uuid4().hex
        saved = default_storage.save(f"importacoes/{uid}_{file.name}", file)
        full_path = default_storage.path(saved)
        service = ImportadorPagamentos(full_path)
        result = service.preview()
        if result.errors and not result.preview:
            return Response({"erros": result.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": uid, "preview": result.preview, "erros": result.errors}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="importar-pagamentos/confirmar")
    def confirmar_importacao(self, request):
        serializer = ImportarPagamentosConfirmacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data["id"]
        # encontra arquivo salvo
        media_path = Path(settings.MEDIA_ROOT) / "importacoes"
        files = list(media_path.glob(f"{uid}_*"))
        if not files:
            return Response({"detail": _("Arquivo não encontrado")}, status=status.HTTP_404_NOT_FOUND)
        file_path = str(files[0])
        importar_pagamentos_async.delay(file_path, str(request.user.id))
        return Response({"detail": _("Importação iniciada")}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"], url_path="relatorios")
    def relatorios(self, request):
        centro_id = request.query_params.get("centro")
        nucleo_id = request.query_params.get("nucleo")
        pi = request.query_params.get("periodo_inicial")
        pf = request.query_params.get("periodo_final")

        def _parse(periodo: str | None) -> datetime | None:
            if not periodo:
                return None
            if not periodo or not periodo.count("-") == 1:
                return None
            dt = parse_date(f"{periodo}-01")
            if dt:
                return datetime(dt.year, dt.month, 1)
            return None

        inicio = _parse(pi)
        fim = _parse(pf)
        if pf and not fim:
            return Response({"detail": _("periodo_final inválido")}, status=400)
        if pi and not inicio:
            return Response({"detail": _("periodo_inicial inválido")}, status=400)

        user = request.user
        if user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            centros_user = [str(c.id) for c in _nucleos_do_usuario(user)]
            if centro_id and centro_id not in centros_user:
                return Response({"detail": _("Sem permissão")}, status=403)
            if not centro_id:
                centro_id = centros_user

        cache_key = f"rel:{centro_id}:{nucleo_id}:{pi}:{pf}"
        result = cache.get(cache_key)
        if result is None:
            result = gerar_relatorio(
                centro=centro_id,
                nucleo=nucleo_id,
                periodo_inicial=inicio,
                periodo_final=fim,
            )
            cache.set(cache_key, result, 600)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="inadimplencias")
    def inadimplencias(self, request):
        centro_id = request.query_params.get("centro")
        nucleo_id = request.query_params.get("nucleo")
        pi = request.query_params.get("periodo_inicial")
        pf = request.query_params.get("periodo_final")

        def _parse(periodo: str | None) -> datetime | None:
            if not periodo or periodo.count("-") != 1:
                return None
            dt = parse_date(f"{periodo}-01")
            if dt:
                return datetime(dt.year, dt.month, 1)
            return None

        inicio = _parse(pi)
        fim = _parse(pf)

        qs = self._lancamentos_base().filter(status=LancamentoFinanceiro.Status.PENDENTE)
        if centro_id:
            qs = qs.filter(centro_custo_id=centro_id)
        if nucleo_id:
            qs = qs.filter(centro_custo__nucleo_id=nucleo_id)
        if inicio:
            qs = qs.filter(data_vencimento__gte=inicio)
        if fim:
            qs = qs.filter(data_vencimento__lt=fim)

        data = []
        now = timezone.now().date()
        for lanc in qs:
            dias_atraso = (now - lanc.data_vencimento.date()).days if lanc.data_vencimento else 0
            data.append(
                {
                    "id": str(lanc.id),
                    "conta": lanc.conta_associado.user.email if lanc.conta_associado else None,
                    "valor": float(lanc.valor),
                    "data_vencimento": lanc.data_vencimento.date() if lanc.data_vencimento else None,
                    "dias_atraso": dias_atraso,
                }
            )
        return Response(data)

    @action(detail=False, methods=["post"], url_path="aportes", permission_classes=[AportePermission])
    def aportes(self, request):
        serializer = AporteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        lancamento = serializer.save()
        return Response(AporteSerializer(lancamento).data, status=status.HTTP_201_CREATED)

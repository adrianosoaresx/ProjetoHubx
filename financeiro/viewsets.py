from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from .models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroLog,
    FinanceiroTaskLog,
    ImportacaoPagamentos,
    LancamentoFinanceiro,
    IntegracaoConfig,
)
from .permissions import IsAssociadoReadOnly, IsCoordenador, IsFinanceiroOrAdmin, IsNotRoot
from .serializers import (
    FinanceiroLogSerializer,
    FinanceiroTaskLogSerializer,
    ImportacaoPagamentosSerializer,
    LancamentoFinanceiroSerializer,
    IntegracaoConfigSerializer,
)
from .services.distribuicao import repassar_receita_ingresso
from .services.auditoria import log_financeiro
from .services.ajustes import ajustar_lancamento
from .services.forecast import calcular_previsao
from .services.exportacao import exportar_para_arquivo
from .views import CentroCustoViewSet, FinanceiroViewSet, parse_periodo


class LancamentoFinanceiroViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Listagem e atualização de lançamentos financeiros."""

    serializer_class = LancamentoFinanceiroSerializer

    def get_permissions(self):  # type: ignore[override]
        if self.action in {"partial_update", "ajustar", "pagar"}:
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

        antigo = {"status": lancamento.status}
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
        log_financeiro(
            FinanceiroLog.Acao.EDITAR_LANCAMENTO,
            request.user,
            antigo,
            {"status": novo_status, "id": str(lancamento.id)},
        )
        serializer = self.get_serializer(lancamento)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def pagar(self, request, *args, **kwargs):
        """Marca um lançamento como pago."""
        lancamento = self.get_object()
        if lancamento.status != LancamentoFinanceiro.Status.PENDENTE:
            return Response(
                {"detail": _("Apenas lançamentos pendentes podem ser pagos")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        antigo = {"status": lancamento.status}
        with transaction.atomic():
            lancamento.status = LancamentoFinanceiro.Status.PAGO
            lancamento.save(update_fields=["status"])
            CentroCusto.objects.filter(pk=lancamento.centro_custo_id).update(
                saldo=F("saldo") + lancamento.valor
            )
            if lancamento.conta_associado_id:
                ContaAssociado.objects.filter(pk=lancamento.conta_associado_id).update(
                    saldo=F("saldo") + lancamento.valor
                )
            if lancamento.tipo == LancamentoFinanceiro.Tipo.INGRESSO_EVENTO:
                repassar_receita_ingresso(lancamento)
        log_financeiro(
            FinanceiroLog.Acao.EDITAR_LANCAMENTO,
            request.user,
            antigo,
            {"status": LancamentoFinanceiro.Status.PAGO, "id": str(lancamento.id)},
        )
        serializer = self.get_serializer(lancamento)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def ajustar(self, request, *args, **kwargs):
        """Realiza ajuste em um lançamento."""
        lancamento = self.get_object()
        valor = request.data.get("valor_corrigido")
        descricao = request.data.get("descricao_motivo", "")
        try:
            ajustar_lancamento(lancamento.id, Decimal(str(valor)), descricao, request.user)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(lancamento)
        return Response(serializer.data)


class ImportacaoPagamentosViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Listagem de registros de importações de pagamentos."""

    serializer_class = ImportacaoPagamentosSerializer
    permission_classes = [IsAuthenticated, IsNotRoot]
    class _Pagination(PageNumberPagination):
        page_size = 10

    pagination_class = _Pagination

    def get_queryset(self):  # type: ignore[override]
        qs = ImportacaoPagamentos.objects.select_related("usuario").all()
        user = self.request.user
        permitido = {UserType.ADMIN, UserType.FINANCEIRO}
        if user.user_type not in permitido:
            qs = qs.filter(usuario=user)
        params = self.request.query_params
        if usuario := params.get("usuario"):
            qs = qs.filter(usuario_id=usuario)
        if arquivo := params.get("arquivo"):
            qs = qs.filter(arquivo__icontains=arquivo)
        inicio = parse_periodo(params.get("periodo_inicial"))
        fim = parse_periodo(params.get("periodo_final"))
        if inicio:
            qs = qs.filter(data_importacao__gte=inicio)
        if fim:
            qs = qs.filter(data_importacao__lt=fim)
        return qs


class FinanceiroLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Consulta dos logs de auditoria do módulo financeiro."""

    serializer_class = FinanceiroLogSerializer
    permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin]

    class _Pagination(PageNumberPagination):
        page_size = 20

    pagination_class = _Pagination

    def get_queryset(self):  # type: ignore[override]
        qs = FinanceiroLog.objects.select_related("usuario")
        params = self.request.query_params
        if acao := params.get("acao"):
            qs = qs.filter(acao=acao)
        if usuario := params.get("usuario"):
            qs = qs.filter(usuario_id=usuario)
        if inicio := params.get("inicio"):
            if dt := parse_date(inicio):
                qs = qs.filter(created_at__date__gte=dt)
        if fim := params.get("fim"):
            if dt := parse_date(fim):
                qs = qs.filter(created_at__date__lt=dt)
        return qs


class RepasseViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Listagem de lançamentos de repasses de receita."""

    serializer_class = LancamentoFinanceiroSerializer
    permission_classes = [
        IsAuthenticated,
        IsNotRoot,
        IsFinanceiroOrAdmin | IsCoordenador | IsAssociadoReadOnly,
    ]

    def get_queryset(self):  # type: ignore[override]
        qs = LancamentoFinanceiro.objects.select_related(
            "centro_custo__evento",
            "centro_custo__nucleo",
            "centro_custo__organizacao",
            "conta_associado__user",
        ).filter(tipo=LancamentoFinanceiro.Tipo.REPASSE)
        user = self.request.user
        if user.user_type == UserType.COORDENADOR and user.nucleo_id:
            qs = qs.filter(centro_custo__nucleo_id=user.nucleo_id)
        elif user.user_type != UserType.ADMIN:
            qs = qs.filter(conta_associado__user=user)
        if evento_id := self.request.query_params.get("evento"):
            qs = qs.filter(centro_custo__evento_id=evento_id)
        return qs

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        fmt = request.query_params.get("format")
        qs = self.get_queryset()
        if fmt in {"csv", "xlsx"}:
            headers = [
                "id",
                "centro_custo",
                "conta_associado",
                "valor",
                "data_lancamento",
                "status",
            ]
            linhas = qs.values_list(
                "id",
                "centro_custo__nome",
                "conta_associado__user__email",
                "valor",
                "data_lancamento",
                "status",
            )
            tmp_name = exportar_para_arquivo(fmt, headers, linhas)
            return FileResponse(open(tmp_name, "rb"), as_attachment=True, filename=f"repasses.{fmt}")
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class FinanceiroForecastViewSet(viewsets.ViewSet):
    """Fornece previsões financeiras agregadas."""

    permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin]

    def list(self, request):  # type: ignore[override]
        params = request.query_params
        escopo = params.get("escopo")
        id_ref = params.get("id")
        if not escopo or not id_ref:
            return Response({"detail": _("Parâmetros obrigatórios")}, status=status.HTTP_400_BAD_REQUEST)
        try:
            periodos = int(params.get("periodos", 6))
        except ValueError:
            return Response({"detail": _("periodos inválido")}, status=status.HTTP_400_BAD_REQUEST)
        if periodos < 1 or periodos > 12:
            return Response({"detail": _("periodos inválido")}, status=status.HTTP_400_BAD_REQUEST)
        crescimento = float(params.get("crescimento_receita", 0))
        reducao = float(params.get("reducao_despesa", 0))
        cache_key = f"fin:forecast:{escopo}:{id_ref}:{periodos}:{crescimento}:{reducao}"
        data = cache.get(cache_key)
        if not data:
            try:
                data = calcular_previsao(
                    escopo,
                    id_ref,
                    periodos,
                    crescimento,
                    reducao,
                )
            except ValueError:
                return Response({"detail": _("escopo inválido")}, status=status.HTTP_400_BAD_REQUEST)
            cache.set(cache_key, data, 6 * 3600)

        fmt = params.get("format")
        if fmt == "csv":
            import csv
            from io import StringIO

            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["mes", "receita", "despesa", "saldo"])
            for item in data["historico"] + data["previsao"]:
                writer.writerow([item["mes"], item["receita"], item["despesa"], item["saldo"]])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="forecast.csv"'
            return resp
        if fmt == "xlsx":
            from io import BytesIO
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.append(["mes", "receita", "despesa", "saldo"])
            for item in data["historico"] + data["previsao"]:
                ws.append([item["mes"], item["receita"], item["despesa"], item["saldo"]])
            stream = BytesIO()
            wb.save(stream)
            stream.seek(0)
            return FileResponse(stream, as_attachment=True, filename="forecast.xlsx")

        payload = {
            "historico": data["historico"],
            "previsao": data["previsao"],
            "parametros": {
                "escopo": escopo,
                "id": id_ref,
                "periodos": periodos,
                "crescimento_receita": crescimento,
                "reducao_despesa": reducao,
            },
        }
        return Response(payload)


class FinanceiroTaskLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Consulta dos logs de tarefas assíncronas."""

    serializer_class = FinanceiroTaskLogSerializer
    permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin]

    class _Pagination(PageNumberPagination):
        page_size = 20

    pagination_class = _Pagination

    def get_queryset(self):  # type: ignore[override]
        qs = FinanceiroTaskLog.objects.all()
        params = self.request.query_params
        if nome := params.get("nome_tarefa"):
            qs = qs.filter(nome_tarefa=nome)
        if status_param := params.get("status"):
            qs = qs.filter(status=status_param)
        if inicio := params.get("inicio"):
            if dt := parse_date(inicio):
                qs = qs.filter(executada_em__date__gte=dt)
        if fim := params.get("fim"):
            if dt := parse_date(fim):
                qs = qs.filter(executada_em__date__lt=dt)
        return qs


class IntegracaoConfigViewSet(viewsets.ModelViewSet):
    """CRUD das configurações de integrações externas."""

    queryset = IntegracaoConfig.objects.all()
    serializer_class = IntegracaoConfigSerializer
    permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin]


__all__ = [
    "CentroCustoViewSet",
    "FinanceiroViewSet",
    "LancamentoFinanceiroViewSet",
    "ImportacaoPagamentosViewSet",
    "FinanceiroLogViewSet",
    "RepasseViewSet",
    "FinanceiroForecastViewSet",
    "FinanceiroTaskLogViewSet",
    "IntegracaoConfigViewSet",
]


from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from ..models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroTaskLog,
    FinanceiroLog,
    ImportacaoPagamentos,
    LancamentoFinanceiro,
)
from ..permissions import (
    IsAssociadoReadOnly,
    IsCoordenador,
    IsFinanceiroOrAdmin,
    IsNotRoot,
)
from ..serializers import (
    AporteSerializer,
    CentroCustoSerializer,
    ImportarPagamentosConfirmacaoSerializer,
    ImportarPagamentosPreviewSerializer,
)
from ..services.cobrancas import _nucleos_do_usuario
from ..services.importacao import ImportadorPagamentos
from ..services.relatorios import _base_queryset, gerar_relatorio
from ..services.exportacao import exportar_para_arquivo
from ..services import metrics
from ..services.auditoria import log_financeiro
from ..services.aportes import estornar_aporte as estornar_aporte_service
from ..tasks.importar_pagamentos import importar_pagamentos_async


def parse_periodo(periodo: str | None) -> datetime | None:
    """Converte ``YYYY-MM`` em :class:`datetime`.

    Levanta ``ValidationError`` se o formato for inválido.
    """
    if not periodo:
        return None
    if periodo.count("-") != 1:
        raise ValidationError("Formato deve ser YYYY-MM")
    dt = parse_date(f"{periodo}-01")
    if not dt:
        raise ValidationError("Formato deve ser YYYY-MM")
    return datetime(dt.year, dt.month, 1)


class AportePermission(IsAuthenticated):
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not super().has_permission(request, view):
            return False
        tipo = request.data.get("tipo", LancamentoFinanceiro.Tipo.APORTE_INTERNO)
        if tipo == LancamentoFinanceiro.Tipo.APORTE_INTERNO:
            return request.user.user_type == UserType.ADMIN
        return True


class CentroCustoViewSet(viewsets.ModelViewSet):
    """CRUD dos centros de custo."""

    queryset = CentroCusto.objects.all()
    serializer_class = CentroCustoSerializer
    permission_classes = [IsAuthenticated, IsNotRoot]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin]
        else:
            self.permission_classes = [IsAuthenticated, IsNotRoot]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset().select_related("organizacao", "nucleo", "evento")
        user = self.request.user
        if user.user_type == UserType.COORDENADOR and user.nucleo_id:
            qs = qs.filter(nucleo_id=user.nucleo_id)
        return qs

    # registra logs de auditoria
    def perform_create(self, serializer):
        centro = serializer.save()
        log_financeiro(
            FinanceiroLog.Acao.EDITAR_CENTRO,
            self.request.user,
            {},
            {"id": str(centro.id), "nome": centro.nome},
        )

    def perform_update(self, serializer):
        antes = {"id": str(serializer.instance.id), "nome": serializer.instance.nome}
        centro = serializer.save()
        log_financeiro(
            FinanceiroLog.Acao.EDITAR_CENTRO,
            self.request.user,
            antes,
            {"id": str(centro.id), "nome": centro.nome},
        )

    def perform_destroy(self, instance):  # type: ignore[override]
        antes = {"id": str(instance.id), "nome": instance.nome}
        super().perform_destroy(instance)
        log_financeiro(
            FinanceiroLog.Acao.EDITAR_CENTRO,
            self.request.user,
            antes,
            {},
        )


class FinanceiroViewSet(viewsets.ViewSet):
    """Endpoints auxiliares do módulo financeiro."""

    permission_classes = [IsAuthenticated, IsNotRoot]

    def get_permissions(self):
        if self.action in {
            "importar_pagamentos",
            "confirmar_importacao",
            "reprocessar_erros",
            "estornar_aporte",
        }:
            self.permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin]
        elif self.action == "relatorios":
            self.permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin | IsCoordenador]
        elif self.action == "inadimplencias":
            self.permission_classes = [
                IsAuthenticated,
                IsNotRoot,
                IsFinanceiroOrAdmin | IsCoordenador | IsAssociadoReadOnly,
            ]
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
        elif user.user_type != UserType.ADMIN:
            qs = qs.filter(conta_associado__user=user)
        return qs

    @action(detail=False, methods=["post"], url_path="importar-pagamentos")
    def importar_pagamentos(self, request):
        metrics.financeiro_importacoes_total.inc()
        serializer = ImportarPagamentosPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data["file"]
        uid = uuid.uuid4().hex
        saved = default_storage.save(f"importacoes/{uid}_{file.name}", file)
        full_path = default_storage.path(saved)
        import_obj = ImportacaoPagamentos.objects.create(
            arquivo=saved,
            usuario=request.user,
            data_importacao=timezone.now(),
        )
        service = ImportadorPagamentos(full_path)
        result = service.preview()
        if result.errors and not result.preview:
            return Response({"erros": result.errors}, status=status.HTTP_400_BAD_REQUEST)
        payload = {
            "id": uid,
            "importacao_id": str(import_obj.id),
            "preview": result.preview,
            "erros": result.errors,
        }
        if result.errors_file:
            payload["token_erros"] = Path(result.errors_file).stem.replace(".errors", "")
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="importar-pagamentos/preview")
    def importar_pagamentos_preview(self, request):
        """Alias para compatibilidade com a rota /preview/ utilizada nos templates."""
        return self.importar_pagamentos(request)

    @action(detail=False, methods=["post"], url_path="importar-pagamentos/confirmar")
    def confirmar_importacao(self, request):
        metrics.financeiro_importacoes_total.inc()
        serializer = ImportarPagamentosConfirmacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data["id"]
        importacao_id = serializer.validated_data["importacao_id"]
        # encontra arquivo salvo
        media_path = Path(settings.MEDIA_ROOT) / "importacoes"
        files = [f for f in media_path.glob(f"{uid}_*") if not f.name.endswith(".errors.csv")]
        if not files:
            return Response({"detail": _("Arquivo não encontrado")}, status=status.HTTP_404_NOT_FOUND)
        file_path = str(files[0])
        importar_pagamentos_async.delay(file_path, str(request.user.id), str(importacao_id))
        log_financeiro(
            FinanceiroLog.Acao.IMPORTAR,
            request.user,
            {"arquivo": file_path, "status": "iniciado"},
            {"importacao_id": str(importacao_id)},
        )
        ImportacaoPagamentos.objects.filter(pk=importacao_id).update(
            arquivo=file_path,
            usuario=request.user,
            status=ImportacaoPagamentos.Status.PROCESSANDO,
        )
        return Response({"detail": _("Importação iniciada")}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["post"], url_path="importar-pagamentos/reprocessar/(?P<token>[\w-]+)")
    def reprocessar_erros(self, request, token: str):
        media_path = Path(settings.MEDIA_ROOT) / "importacoes"
        err_file = media_path / f"{token}.errors.csv"
        if not err_file.exists():
            return Response({"detail": _("Arquivo não encontrado")}, status=status.HTTP_404_NOT_FOUND)
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": _("Arquivo ausente")}, status=status.HTTP_400_BAD_REQUEST)
        saved = default_storage.save(f"importacoes/{uuid.uuid4().hex}_{uploaded.name}", uploaded)
        full_path = default_storage.path(saved)
        service = ImportadorPagamentos(full_path)
        total, errors = service.process()
        if errors:
            return Response({"erros": errors}, status=status.HTTP_400_BAD_REQUEST)
        err_file.unlink(missing_ok=True)
        return Response({"detail": _("Reprocessamento concluído"), "total": total})

    @action(detail=False, methods=["get"], url_path="relatorios")
    def relatorios(self, request):
        metrics.financeiro_relatorios_total.inc()
        params = request.query_params
        centro_id: str | list[str] | None = params.getlist("centro") or params.get("centro")
        nucleo_id = params.get("nucleo")
        try:
            inicio = parse_periodo(params.get("periodo_inicial"))
            fim = parse_periodo(params.get("periodo_final"))
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

        user = request.user
        if user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            centros_user = [str(centro.id) for centro, _ in _nucleos_do_usuario(user)]
            if isinstance(centro_id, list):
                if not set(centro_id).issubset(set(centros_user)):
                    return Response({"detail": _("Sem permissão")}, status=403)
                if not centro_id:
                    centro_id = centros_user
            else:
                if centro_id and centro_id not in centros_user:
                    return Response({"detail": _("Sem permissão")}, status=403)
                if not centro_id:
                    centro_id = centros_user

        tipo = params.get("tipo")
        cache_centro = "|".join(sorted(centro_id)) if isinstance(centro_id, list) else centro_id
        cache_key = f"rel:{cache_centro}:{nucleo_id}:{params.get('periodo_inicial')}:{params.get('periodo_final')}:{tipo}"
        result = cache.get(cache_key)
        if result is None:
            result = gerar_relatorio(
                centro=centro_id,
                nucleo=nucleo_id,
                periodo_inicial=inicio,
                periodo_final=fim,
                tipo=tipo,
            )
            cache.set(cache_key, result, 600)

        fmt = params.get("format")
        if fmt in {"csv", "xlsx"}:
            qs_csv = _base_queryset(centro_id, nucleo_id, inicio, fim)
            if tipo == "receitas":
                qs_csv = qs_csv.filter(valor__gt=0)
            elif tipo == "despesas":
                qs_csv = qs_csv.filter(valor__lt=0)
            linhas = [
                [
                    lanc.data_lancamento.date(),
                    lanc.get_tipo_display(),
                    float(lanc.valor),
                    lanc.status,
                    lanc.centro_custo.nome,
                ]
                for lanc in qs_csv
            ]
            headers = ["data", "categoria", "valor", "status", "centro de custo"]
            try:
                tmp_name = exportar_para_arquivo(fmt, headers, linhas)
            except RuntimeError:
                return Response({"detail": _("openpyxl não disponível")}, status=500)
            return FileResponse(open(tmp_name, "rb"), as_attachment=True, filename=f"relatorio.{fmt}")

        return Response(result)

    @action(detail=False, methods=["get"], url_path="inadimplencias")
    def inadimplencias(self, request):
        metrics.financeiro_relatorios_total.inc()
        params = request.query_params
        centro_id = params.get("centro")
        nucleo_id = params.get("nucleo")
        try:
            inicio = parse_periodo(params.get("periodo_inicial"))
            fim = parse_periodo(params.get("periodo_final"))
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

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
                    "centro": lanc.centro_custo.nome,
                    "conta": lanc.conta_associado.user.email if lanc.conta_associado else None,
                    "status": lanc.status,
                    "valor": float(lanc.valor),
                    "data_vencimento": lanc.data_vencimento.date() if lanc.data_vencimento else None,
                    "dias_atraso": dias_atraso,
                }
            )
        fmt = params.get("format")
        if fmt in {"csv", "xlsx"}:
            headers = ["ID", "Conta", "Status", "Valor", "Data Vencimento", "Dias Atraso"]
            linhas = [
                [
                    item["id"],
                    item["conta"],
                    item["status"],
                    item["valor"],
                    item["data_vencimento"],
                    item["dias_atraso"],
                ]
                for item in data
            ]
            try:
                tmp_name = exportar_para_arquivo(fmt, headers, linhas)
            except RuntimeError:
                return Response({"detail": _("openpyxl não disponível")}, status=500)
            filename = f"inadimplencias.{fmt}"
            return FileResponse(open(tmp_name, "rb"), as_attachment=True, filename=filename)

        return Response(data)

    @action(detail=False, methods=["post"], url_path="aportes", permission_classes=[AportePermission])
    def aportes(self, request):
        serializer = AporteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        lancamento = serializer.save()
        return Response(AporteSerializer(lancamento).data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path="aportes/(?P<aporte_id>[\w-]+)/estornar",
    )
    def estornar_aporte(self, request, aporte_id: str):
        try:
            lancamento = estornar_aporte_service(aporte_id, request.user)
        except Exception as exc:  # pragma: no cover - validações
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AporteSerializer(lancamento).data)


def _is_financeiro_or_admin(user) -> bool:
    permitido = {UserType.ADMIN, UserType.FINANCEIRO}
    return user.is_authenticated and user.user_type in permitido


@login_required
@user_passes_test(_is_financeiro_or_admin)
def importar_pagamentos_view(request):
    return render(request, "financeiro/importar_pagamentos.html")


@login_required
@user_passes_test(_is_financeiro_or_admin)
def relatorios_view(request):
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
    }
    return render(request, "financeiro/relatorios.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def lancamentos_list_view(request):
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
    }
    return render(request, "financeiro/lancamentos_list.html", context)


@login_required
@user_passes_test(_is_financeiro_or_admin)
def inadimplencias_view(request):
    centros = CentroCusto.objects.all()
    nucleos = {c.nucleo for c in centros if c.nucleo}
    context = {
        "centros": centros,
        "nucleos": list(nucleos),
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
@user_passes_test(_is_financeiro_or_admin)
def forecast_view(request):
    """Tela com previsão financeira."""
    return render(request, "financeiro/forecast.html")

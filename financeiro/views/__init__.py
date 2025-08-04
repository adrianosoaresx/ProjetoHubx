from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import F
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render

try:
    from openpyxl import Workbook
except Exception:  # pragma: no cover - opcional
    Workbook = None  # type: ignore
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro, FinanceiroTaskLog
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
from ..services.distribuicao import repassar_receita_ingresso
from ..services.importacao import ImportadorPagamentos
from ..services.relatorios import _base_queryset, gerar_relatorio
from ..tasks.importar_pagamentos import importar_pagamentos_async


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


class FinanceiroViewSet(viewsets.ViewSet):
    """Endpoints auxiliares do módulo financeiro."""

    permission_classes = [IsAuthenticated, IsNotRoot]

    def get_permissions(self):
        if self.action in {"importar_pagamentos", "confirmar_importacao", "reprocessar_erros", "aportes"}:
            self.permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin]
        elif self.action == "relatorios":
            self.permission_classes = [IsAuthenticated, IsNotRoot, IsFinanceiroOrAdmin | IsCoordenador]
        elif self.action == "inadimplencias":
            self.permission_classes = [
                IsAuthenticated,
                IsNotRoot,
                IsFinanceiroOrAdmin | IsCoordenador | IsAssociadoReadOnly,
            ]
        else:
            self.permission_classes = [IsAuthenticated, IsNotRoot]
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
        payload = {"id": uid, "preview": result.preview, "erros": result.errors}
        if result.errors_file:
            payload["token_erros"] = Path(result.errors_file).stem.replace(".errors", "")
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="importar-pagamentos/preview")
    def importar_pagamentos_preview(self, request):
        """Alias para compatibilidade com a rota /preview/ utilizada nos templates."""
        return self.importar_pagamentos(request)

    @action(detail=False, methods=["post"], url_path="importar-pagamentos/confirmar")
    def confirmar_importacao(self, request):
        serializer = ImportarPagamentosConfirmacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data["id"]
        # encontra arquivo salvo
        media_path = Path(settings.MEDIA_ROOT) / "importacoes"
        files = [f for f in media_path.glob(f"{uid}_*") if not f.name.endswith(".errors.csv")]
        if not files:
            return Response({"detail": _("Arquivo não encontrado")}, status=status.HTTP_404_NOT_FOUND)
        file_path = str(files[0])
        importar_pagamentos_async.delay(file_path, str(request.user.id))
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

        fmt = request.query_params.get("format")
        if fmt == "csv":
            import csv

            tmp = NamedTemporaryFile(delete=False, suffix=".csv")
            qs_csv = _base_queryset(centro_id, nucleo_id, inicio, fim)
            writer = csv.writer(tmp)
            writer.writerow(["data", "categoria", "valor", "status", "centro de custo"])
            for lanc in qs_csv:
                writer.writerow(
                    [
                        lanc.data_lancamento.date(),
                        lanc.get_tipo_display(),
                        float(lanc.valor),
                        lanc.status,
                        lanc.centro_custo.nome,
                    ]
                )
            tmp.close()
            return FileResponse(open(tmp.name, "rb"), as_attachment=True, filename="relatorio.csv")
        if fmt == "xlsx":
            if not Workbook:
                return Response({"detail": _("openpyxl não disponível")}, status=500)
            tmp = NamedTemporaryFile(delete=False, suffix=".xlsx")
            wb = Workbook()
            ws = wb.active
            ws.append(["Mês", "Receitas", "Despesas", "Saldo"])
            for row in result["serie"]:
                ws.append([row["mes"], row["receitas"], row["despesas"], row["saldo"]])
            ws.append([])
            ws.append(["Mês", "Pendentes", "Quitadas"])
            for row in result["inadimplencia"]:
                ws.append([row["mes"], row["pendentes"], row["quitadas"]])
            wb.save(tmp.name)
            tmp.close()
            return FileResponse(open(tmp.name, "rb"), as_attachment=True, filename="relatorio.xlsx")

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
                    "status": lanc.status,
                    "valor": float(lanc.valor),
                    "data_vencimento": lanc.data_vencimento.date() if lanc.data_vencimento else None,
                    "dias_atraso": dias_atraso,
                }
            )
        fmt = request.query_params.get("format")
        if fmt in {"csv", "xlsx"}:
            tmp = NamedTemporaryFile(delete=False, suffix=f".{fmt}")
            if fmt == "csv":
                import csv

                writer = csv.writer(tmp)
                writer.writerow(["ID", "Conta", "Status", "Valor", "Data Vencimento", "Dias Atraso"])
                for item in data:
                    writer.writerow(
                        [
                            item["id"],
                            item["conta"],
                            item["status"],
                            item["valor"],
                            item["data_vencimento"],
                            item["dias_atraso"],
                        ]
                    )
            else:
                if not Workbook:
                    return Response({"detail": _("openpyxl não disponível")}, status=500)
                wb = Workbook()
                ws = wb.active
                ws.append(["ID", "Conta", "Status", "Valor", "Data Vencimento", "Dias Atraso"])
                for item in data:
                    ws.append(
                        [
                            item["id"],
                            item["conta"],
                            item["status"],
                            item["valor"],
                            item["data_vencimento"],
                            item["dias_atraso"],
                        ]
                    )
                wb.save(tmp.name)
            tmp.close()
            filename = f"inadimplencias.{fmt}"
            return FileResponse(open(tmp.name, "rb"), as_attachment=True, filename=filename)

        return Response(data)

    @action(detail=False, methods=["post"], url_path="aportes", permission_classes=[AportePermission])
    def aportes(self, request):
        serializer = AporteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        lancamento = serializer.save()
        return Response(AporteSerializer(lancamento).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch"],
        url_path="quitar",
        permission_classes=[IsFinanceiroOrAdmin, IsNotRoot],
    )
    def quitar(self, request, pk=None):
        lancamento = get_object_or_404(self._lancamentos_base(), pk=pk)
        if lancamento.status == LancamentoFinanceiro.Status.PAGO:
            return Response({"detail": _("Lançamento já quitado")}, status=400)
        with transaction.atomic():
            lancamento.status = LancamentoFinanceiro.Status.PAGO
            lancamento.save(update_fields=["status"])
            CentroCusto.objects.filter(pk=lancamento.centro_custo_id).update(saldo=F("saldo") + lancamento.valor)
            if lancamento.conta_associado_id:
                ContaAssociado.objects.filter(pk=lancamento.conta_associado_id).update(
                    saldo=F("saldo") + lancamento.valor
                )
            if lancamento.tipo == LancamentoFinanceiro.Tipo.INGRESSO_EVENTO:
                repassar_receita_ingresso(lancamento)
        return Response({"detail": _("Lançamento quitado")})


def _is_financeiro_or_admin(user) -> bool:
    permitido = {UserType.ADMIN}
    tipo_financeiro = getattr(UserType, "FINANCEIRO", None)
    if tipo_financeiro:
        permitido.add(tipo_financeiro)
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

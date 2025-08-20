from __future__ import annotations

import csv
import io
from datetime import datetime

from openpyxl import Workbook

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import UserType
from audit.services import hash_ip, log_audit

from .models import DashboardFilter, DashboardCustomMetric
from .serializers import DashboardFilterSerializer, DashboardCustomMetricSerializer
from .services import DashboardMetricsService, DashboardService, check_achievements
from .custom_metrics import DashboardCustomMetricService
from core.permissions import IsModeratorUser



class IsAdminOrCoordenador(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.user_type in {UserType.ADMIN, UserType.COORDENADOR, UserType.ROOT}


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        filter_id = request.query_params.get("filter_id")
        if filter_id:
            filtro = get_object_or_404(DashboardFilter, pk=filter_id, user=request.user)
            params = filtro.filtros
        else:
            params = request.query_params
        periodo = params.get("periodo", "mensal")
        inicio = params.get("inicio")
        fim = params.get("fim")
        escopo = params.get("escopo", "auto")
        inicio_dt = datetime.fromisoformat(inicio) if inicio else None
        fim_dt = datetime.fromisoformat(fim) if fim else None
        filters = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            val = params.get(key)
            if val:
                filters[key] = val
        metricas_list = params.getlist("metricas") if hasattr(params, "getlist") else params.get("metricas")
        if metricas_list:
            filters["metricas"] = metricas_list
        try:
            data = DashboardMetricsService.get_metrics(
                request.user, periodo, inicio_dt, fim_dt, escopo=escopo, **filters
            )
        except PermissionError:
            return Response({"detail": "Forbidden"}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrCoordenador])
    def export(self, request):
        formato = request.query_params.get("formato", "csv")
        periodo = request.query_params.get("periodo", "mensal")
        inicio = request.query_params.get("inicio")
        fim = request.query_params.get("fim")
        inicio_dt = datetime.fromisoformat(inicio) if inicio else None
        fim_dt = datetime.fromisoformat(fim) if fim else None
        filtros = request.query_params.dict()
        filtros.pop("formato", None)
        metadata = {"filtros": filtros, "formato": formato}
        ip_hash = hash_ip(request.META.get("REMOTE_ADDR", ""))
        try:
            data = DashboardMetricsService.get_metrics(request.user, periodo, inicio_dt, fim_dt)
        except PermissionError:
            log_audit(
                request.user,
                f"EXPORT_{formato.upper()}",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                status="ERROR",
                metadata=metadata,
            )
            return Response({"detail": "Forbidden"}, status=403)
        except ValueError as exc:
            log_audit(
                request.user,
                f"EXPORT_{formato.upper()}",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                status="ERROR",
                metadata={**metadata, "error": str(exc)},
            )
            return Response({"detail": str(exc)}, status=400)
        if formato == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Métrica", "Total", "Crescimento"])
            for key, value in data.items():
                writer.writerow([key, value["total"], value["crescimento"]])
            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=dashboard.csv"
            log_audit(
                request.user,
                "EXPORT_CSV",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                metadata=metadata,
            )
            return response
        elif formato == "pdf":
            try:
                from weasyprint import HTML
            except Exception:
                log_audit(
                    request.user,
                    "EXPORT_PDF",
                    object_type="DashboardMetrics",
                    ip_hash=ip_hash,
                    status="ERROR",
                    metadata=metadata,
                )
                return Response({"detail": "PDF indisponível"}, status=500)
            html = render_to_string("dashboard/export_pdf.html", {"metrics": data})
            pdf_bytes = HTML(string=html).write_pdf()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = "attachment; filename=dashboard.pdf"
            log_audit(
                request.user,
                "EXPORT_PDF",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                metadata=metadata,
            )
            return response
        elif formato == "xlsx":
            wb = Workbook()
            ws = wb.active
            ws.title = "Métricas"
            ws.append(["Métrica", "Total", "Crescimento"])
            for key, value in data.items():
                ws.append([key, value["total"], value["crescimento"]])
            output = io.BytesIO()
            wb.save(output)
            response = HttpResponse(
                output.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = "attachment; filename=dashboard.xlsx"
            log_audit(
                request.user,
                "EXPORT_XLSX",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                metadata=metadata,
            )
            return response
        log_audit(
            request.user,
            f"EXPORT_{formato.upper()}",
            object_type="DashboardMetrics",
            ip_hash=ip_hash,
            status="ERROR",
            metadata=metadata,
        )
        return Response({"detail": _("Formato inválido.")}, status=400)

    @action(detail=False, methods=["get"], url_path="comparativo")
    def comparativo(self, request):
        metricas = request.query_params.getlist("metricas") or ["num_users"]
        escopo = request.query_params.get("escopo", "organizacao")
        filters = {}
        if escopo == "nucleo":
            nucleo_id = request.query_params.get("nucleo_id")
            if nucleo_id:
                filters["nucleo_id"] = nucleo_id
        atual = DashboardMetricsService.get_metrics(request.user, escopo=escopo, metricas=metricas, **filters)
        media = DashboardService.medias_globais(metricas, por=escopo)
        return Response({"atual": atual, "media": media})


class DashboardFilterViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardFilterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DashboardFilter.objects.filter(user=self.request.user)
        public_qs = DashboardFilter.objects.filter(publico=True).exclude(user=self.request.user)
        if self.request.user.user_type == UserType.ROOT:
            qs = qs | public_qs
        else:
            qs = qs | public_qs.filter(user__organizacao=self.request.user.organizacao)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        check_achievements(self.request.user)


class DashboardCustomMetricViewSet(viewsets.ModelViewSet):
    queryset = DashboardCustomMetric.objects.all()
    serializer_class = DashboardCustomMetricSerializer

    def get_permissions(self):  # type: ignore[override]
        if self.action in {"list", "retrieve", "execute"}:
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            self.permission_classes = [IsModeratorUser]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def execute(self, request, pk=None):
        metric = self.get_object()
        params = request.query_params.dict()
        total = DashboardCustomMetricService.execute(metric.query_spec, **params)
        return Response({"code": metric.code, "total": total})

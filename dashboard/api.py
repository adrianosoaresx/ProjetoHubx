from __future__ import annotations

import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import UserType
from audit.services import hash_ip, log_audit
from tokens.utils import get_client_ip

from .models import DashboardFilter, DashboardCustomMetric
from .serializers import DashboardFilterSerializer, DashboardCustomMetricSerializer
from .services import DashboardMetricsService, DashboardService
from .custom_metrics import DashboardCustomMetricService
from .constants import METRICAS_INFO
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
        inicio_dt = parse_datetime(inicio) if inicio else None
        if inicio and inicio_dt is None:
            return Response({"detail": "inicio inválido"}, status=400)
        if inicio_dt and timezone.is_naive(inicio_dt):
            inicio_dt = timezone.make_aware(inicio_dt)
        fim_dt = parse_datetime(fim) if fim else None
        if fim and fim_dt is None:
            return Response({"detail": "fim inválido"}, status=400)
        if fim_dt and timezone.is_naive(fim_dt):
            fim_dt = timezone.make_aware(fim_dt)
        if inicio_dt and fim_dt and inicio_dt > fim_dt:
            return Response({"detail": "inicio deve ser menor ou igual a fim"}, status=400)
        filters = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            val = params.get(key)
            if val:
                filters[key] = val
        metricas_list = (
            params.getlist("metricas")
            if hasattr(params, "getlist")
            else params.get("metricas")
        )
        if metricas_list:
            if isinstance(metricas_list, str):
                metricas_list = [metricas_list]
            valid_metricas = set(METRICAS_INFO.keys()) | set(
                DashboardCustomMetric.objects.values_list("code", flat=True)
            )
            invalid = [m for m in metricas_list if m not in valid_metricas]
            if invalid:
                if len(invalid) == 1:
                    return Response({"detail": f"Métrica inválida: {invalid[0]}"}, status=400)
                return Response(
                    {"detail": f"Métricas inválidas: {', '.join(invalid)}"}, status=400
                )
            filters["metricas"] = metricas_list
        try:
            data, _ = DashboardMetricsService.get_metrics(
                request.user, periodo, inicio_dt, fim_dt, escopo=escopo, **filters
            )
        except PermissionError:
            return Response({"detail": "Forbidden"}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrCoordenador])
    def export(self, request):
        formato = request.query_params.get("formato", "pdf")
        periodo = request.query_params.get("periodo", "mensal")
        inicio = request.query_params.get("inicio")
        fim = request.query_params.get("fim")
        filters = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            val = request.query_params.get(key)
            if val:
                filters[key] = val
        metricas_list = request.query_params.getlist("metricas")
        filtros = request.query_params.dict()
        if metricas_list:
            filtros["metricas"] = metricas_list
        filtros.pop("formato", None)
        metadata = {"filtros": filtros, "formato": formato}
        ip_hash = hash_ip(get_client_ip(request))
        if metricas_list:
            valid_metricas = set(METRICAS_INFO.keys()) | set(
                DashboardCustomMetric.objects.values_list("code", flat=True)
            )
            invalid = [m for m in metricas_list if m not in valid_metricas]
            if invalid:
                error_msg = (
                    f"Métrica inválida: {invalid[0]}"
                    if len(invalid) == 1
                    else f"Métricas inválidas: {', '.join(invalid)}"
                )
                log_audit(
                    request.user,
                    f"EXPORT_{formato.upper()}",
                    object_type="DashboardMetrics",
                    ip_hash=ip_hash,
                    status="ERROR",
                    metadata={**metadata, "error": error_msg},
                )
                return Response({"detail": error_msg}, status=400)
            filters["metricas"] = metricas_list
        inicio_dt = parse_datetime(inicio) if inicio else None
        if inicio and inicio_dt is None:
            log_audit(
                request.user,
                f"EXPORT_{formato.upper()}",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                status="ERROR",
                metadata={**metadata, "error": "inicio inválido"},
            )
            return Response({"detail": "inicio inválido"}, status=400)
        if inicio_dt and timezone.is_naive(inicio_dt):
            inicio_dt = timezone.make_aware(inicio_dt)
        fim_dt = parse_datetime(fim) if fim else None
        if fim and fim_dt is None:
            log_audit(
                request.user,
                f"EXPORT_{formato.upper()}",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                status="ERROR",
                metadata={**metadata, "error": "fim inválido"},
            )
            return Response({"detail": "fim inválido"}, status=400)
        if fim_dt and timezone.is_naive(fim_dt):
            fim_dt = timezone.make_aware(fim_dt)
        if inicio_dt and fim_dt and inicio_dt > fim_dt:
            log_audit(
                request.user,
                f"EXPORT_{formato.upper()}",
                object_type="DashboardMetrics",
                ip_hash=ip_hash,
                status="ERROR",
                metadata={**metadata, "error": "inicio deve ser menor ou igual a fim"},
            )
            return Response({"detail": "inicio deve ser menor ou igual a fim"}, status=400)
        try:
            data, _ = DashboardMetricsService.get_metrics(
                request.user, periodo, inicio_dt, fim_dt, **filters
            )
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
        if formato == "pdf":
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
        atual, _ = DashboardMetricsService.get_metrics(
            request.user, escopo=escopo, metricas=metricas, **filters
        )
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

from __future__ import annotations

import csv
import io
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import UserType

from .models import DashboardFilter
from .serializers import DashboardFilterSerializer
from .services import DashboardMetricsService


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
        inicio_dt = datetime.fromisoformat(inicio) if inicio else None
        fim_dt = datetime.fromisoformat(fim) if fim else None
        data = DashboardMetricsService.get_metrics(request.user, periodo, inicio_dt, fim_dt)
        return Response(data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrCoordenador])
    def export(self, request):
        formato = request.query_params.get("formato", "csv")
        periodo = request.query_params.get("periodo", "mensal")
        inicio = request.query_params.get("inicio")
        fim = request.query_params.get("fim")
        inicio_dt = datetime.fromisoformat(inicio) if inicio else None
        fim_dt = datetime.fromisoformat(fim) if fim else None
        data = DashboardMetricsService.get_metrics(request.user, periodo, inicio_dt, fim_dt)
        if formato == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Métrica", "Total", "Crescimento"])
            for key, value in data.items():
                writer.writerow([key, value["total"], value["crescimento"]])
            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = "attachment; filename=dashboard.csv"
            return response
        elif formato == "pdf":
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            y = 750
            pdf.drawString(50, y, "Métricas do Dashboard")
            y -= 20
            for key, value in data.items():
                pdf.drawString(50, y, f"{key}: {value['total']} ({value['crescimento']:.1f}%)")
                y -= 15
            pdf.showPage()
            pdf.save()
            response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
            response["Content-Disposition"] = "attachment; filename=dashboard.pdf"
            return response
        return Response({"detail": _("Formato inválido.")}, status=400)


class DashboardFilterViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardFilterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DashboardFilter.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

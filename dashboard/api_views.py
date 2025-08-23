"""API views for dashboard-related endpoints."""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .services import get_feed_counts, get_top_authors, get_top_tags


class CanViewMetrics(permissions.BasePermission):
    """Permissão para acesso às métricas do dashboard."""

    def has_permission(self, request: Request, view: APIView) -> bool:  # pragma: no cover - simples
        return request.user.has_perm("dashboard.view_metrics")


class FeedMetricsView(APIView):
    """Retorna métricas do feed para o dashboard."""

    permission_classes = [permissions.IsAuthenticated, CanViewMetrics]

    def get(self, request: Request, *args, **kwargs) -> Response:
        org = request.query_params.get("organizacao")
        inicio_str = request.query_params.get("inicio")
        fim_str = request.query_params.get("fim")
        inicio = parse_datetime(inicio_str) if inicio_str else None
        if inicio_str and inicio is None:
            return Response({"detail": "data_inicio inválida"}, status=400)
        if inicio and timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio)
        fim = parse_datetime(fim_str) if fim_str else None
        if fim_str and fim is None:
            return Response({"detail": "data_fim inválida"}, status=400)
        if fim and timezone.is_naive(fim):
            fim = timezone.make_aware(fim)

        counts = get_feed_counts(org, inicio, fim)
        tags = get_top_tags(org, inicio, fim)
        authors = get_top_authors(org, inicio, fim)
        return Response({"counts": counts, "top_tags": tags, "top_authors": authors})


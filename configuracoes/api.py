from __future__ import annotations

import time

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import metrics
from .models import ConfiguracaoConta
from .serializers import ConfiguracaoContaSerializer
from .services import get_configuracao_conta


class ConfiguracaoContaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self) -> ConfiguracaoConta:
        return get_configuracao_conta(self.request.user)

    @extend_schema(
        responses=ConfiguracaoContaSerializer,
        examples=[
            OpenApiExample(
                "Exemplo",
                value={
                    "receber_notificacoes_email": True,
                    "frequencia_notificacoes_email": "imediata",
                    "receber_notificacoes_whatsapp": False,
                    "frequencia_notificacoes_whatsapp": "diaria",
                    "idioma": "pt-BR",
                    "tema": "claro",
                    "hora_notificacao_diaria": "08:00:00",
                    "hora_notificacao_semanal": "08:00:00",
                    "dia_semana_notificacao": 0,
                },
            )
        ],
    )
    def get(self, request):
        start = time.monotonic()
        serializer = ConfiguracaoContaSerializer(self.get_object())
        resp = Response(serializer.data)
        metrics.config_api_latency_seconds.labels(method="GET").observe(time.monotonic() - start)
        return resp

    @extend_schema(
        request=ConfiguracaoContaSerializer,
        responses=ConfiguracaoContaSerializer,
        examples=[
            OpenApiExample(
                "Atualização completa",
                request_only=True,
                value={"tema": "escuro", "idioma": "en-US"},
            )
        ],
    )
    def put(self, request):
        start = time.monotonic()
        obj = self.get_object()
        serializer = ConfiguracaoContaSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        resp = Response(serializer.data)
        metrics.config_api_latency_seconds.labels(method="PUT").observe(time.monotonic() - start)
        return resp

    @extend_schema(
        request=ConfiguracaoContaSerializer,
        responses=ConfiguracaoContaSerializer,
        examples=[
            OpenApiExample(
                "Atualização parcial",
                request_only=True,
                value={"receber_notificacoes_email": False},
            )
        ],
    )
    def patch(self, request):
        start = time.monotonic()
        obj = self.get_object()
        serializer = ConfiguracaoContaSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        resp = Response(serializer.data)
        metrics.config_api_latency_seconds.labels(method="PATCH").observe(time.monotonic() - start)
        return resp

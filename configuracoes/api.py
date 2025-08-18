from __future__ import annotations

import time

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.views import APIView

from . import metrics
from .serializers import (
    ConfiguracaoContaSerializer,
    ConfiguracaoContextualSerializer,
)
from .services import get_configuracao_conta, get_user_preferences
from .models import ConfiguracaoConta, ConfiguracaoContextual
from notificacoes.models import NotificationTemplate, Canal
from notificacoes.services.notificacoes import enviar_para_usuario


class ConfiguracaoContaViewSet(ViewSet):
    """ViewSet para leitura e atualização das preferências do usuário."""

    permission_classes = [IsAuthenticated]

    def _get_object(self) -> ConfiguracaoConta:
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
                    "receber_notificacoes_push": True,
                    "frequencia_notificacoes_push": "imediata",
                    "idioma": "pt-BR",
                    "tema": "claro",
                    "hora_notificacao_diaria": "08:00:00",
                    "hora_notificacao_semanal": "08:00:00",
                    "dia_semana_notificacao": 0,
                },
            )
        ],
    )
    def retrieve(self, request) -> Response:
        start = time.monotonic()
        serializer = ConfiguracaoContaSerializer(self._get_object())
        resp = Response(serializer.data)
        metrics.config_api_latency_seconds.labels(method="GET").observe(
            time.monotonic() - start
        )
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
    def update(self, request) -> Response:
        start = time.monotonic()
        obj = self._get_object()
        serializer = ConfiguracaoContaSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        resp = Response(serializer.data)
        metrics.config_api_latency_seconds.labels(method="PUT").observe(
            time.monotonic() - start
        )
        return resp

    @extend_schema(
        request=ConfiguracaoContaSerializer,
        responses=ConfiguracaoContaSerializer,
        examples=[
            OpenApiExample(
                "Atualização parcial",
                request_only=True,
                value={"receber_notificacoes_push": False},
            ),
        ],
    )
    def partial_update(self, request) -> Response:
        start = time.monotonic()
        obj = self._get_object()
        serializer = ConfiguracaoContaSerializer(
            obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        resp = Response(serializer.data)
        metrics.config_api_latency_seconds.labels(method="PATCH").observe(
            time.monotonic() - start
        )
        return resp


class ConfiguracaoContextualViewSet(ModelViewSet):
    """CRUD das configurações contextuais via API."""

    serializer_class = ConfiguracaoContextualSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # pragma: no cover - simples filtro
        return ConfiguracaoContextual.objects.filter(user=self.request.user)

    def perform_create(self, serializer):  # pragma: no cover - simples
        serializer.save(user=self.request.user)


class TestarNotificacaoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        canal = request.data.get("canal", Canal.EMAIL)
        escopo_tipo = request.data.get("escopo_tipo")
        escopo_id = request.data.get("escopo_id")
        prefs = get_user_preferences(request.user, escopo_tipo, escopo_id)
        if canal == Canal.EMAIL and not prefs.receber_notificacoes_email:
            return Response({"detail": "canal desabilitado"}, status=400)
        if canal == Canal.WHATSAPP and not prefs.receber_notificacoes_whatsapp:
            return Response({"detail": "canal desabilitado"}, status=400)
        if canal == Canal.PUSH and not prefs.receber_notificacoes_push:
            return Response({"detail": "canal desabilitado"}, status=400)
        template, _ = NotificationTemplate.objects.get_or_create(
            codigo=f"teste_{canal}",
            defaults={
                "assunto": "Teste",
                "corpo": "Mensagem de teste",
                "canal": canal,
            },
        )
        enviar_para_usuario(
            request.user,
            template.codigo,
            {},
            escopo_tipo=escopo_tipo,
            escopo_id=escopo_id,
        )
        return Response({"detail": "enviado"})


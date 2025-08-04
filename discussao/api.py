from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType
from .models import RespostaDiscussao, Tag, TopicoDiscussao
from .serializers import (
    RespostaDiscussaoSerializer,
    TagSerializer,
    TopicoDiscussaoSerializer,
)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("nome")
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class TopicoViewSet(viewsets.ModelViewSet):
    queryset = (
        TopicoDiscussao.objects.select_related("categoria", "autor", "melhor_resposta")
        .prefetch_related("tags", "respostas__autor")
        .all()
    )
    serializer_class = TopicoDiscussaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        tags_param = self.request.query_params.get("tags")
        if tags_param:
            names = [t.strip() for t in tags_param.split(",") if t.strip()]
            qs = qs.filter(tags__nome__in=names).distinct()
        return qs

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

    def perform_update(self, serializer):
        if not self._can_edit(serializer.instance):
            raise PermissionDenied("Prazo de edição expirado.")
        serializer.save()

    def _can_edit(self, obj: TopicoDiscussao) -> bool:
        if timezone.now() - obj.created > timedelta(minutes=15):
            return self.request.user.get_tipo_usuario in {
                UserType.ADMIN.value,
                UserType.ROOT.value,
            }
        return obj.autor == self.request.user or self.request.user.get_tipo_usuario in {
            UserType.ADMIN.value,
            UserType.ROOT.value,
        }

    @action(detail=True, methods=["post"], url_path="marcar-melhor-resposta")
    def marcar_melhor_resposta(self, request, pk=None):
        topico = self.get_object()
        resposta_id = request.data.get("resposta_id")
        resposta = get_object_or_404(topico.respostas, id=resposta_id)
        if request.user not in {topico.autor} and request.user.get_tipo_usuario not in {
            UserType.ADMIN.value,
            UserType.ROOT.value,
        }:
            return Response(status=403)
        with transaction.atomic():
            topico.melhor_resposta = resposta
            topico.save(update_fields=["melhor_resposta"])
        serializer = self.get_serializer(topico)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="fechar")
    def fechar(self, request, pk=None):
        topico = self.get_object()
        if request.user not in {topico.autor} and request.user.get_tipo_usuario not in {
            UserType.ADMIN.value,
            UserType.ROOT.value,
        }:
            return Response(status=403)
        with transaction.atomic():
            topico.fechado = True
            topico.save(update_fields=["fechado"])
        serializer = self.get_serializer(topico)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="reabrir")
    def reabrir(self, request, pk=None):
        topico = self.get_object()
        if request.user.get_tipo_usuario not in {UserType.ADMIN.value, UserType.ROOT.value}:
            return Response(status=403)
        with transaction.atomic():
            topico.fechado = False
            topico.save(update_fields=["fechado"])
        serializer = self.get_serializer(topico)
        return Response(serializer.data)


class RespostaViewSet(viewsets.ModelViewSet):
    queryset = RespostaDiscussao.objects.select_related("autor", "topico").all()
    serializer_class = RespostaDiscussaoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        topico = serializer.validated_data["topico"]
        if topico.fechado:
            raise PermissionDenied("Tópico fechado para novas respostas.")
        serializer.save(autor=self.request.user)

    def perform_update(self, serializer):
        if not self._can_edit(serializer.instance):
            raise PermissionDenied("Prazo de edição expirado.")
        serializer.save()

    def _can_edit(self, obj: RespostaDiscussao) -> bool:
        if timezone.now() - obj.created > timedelta(minutes=15):
            return self.request.user.get_tipo_usuario in {
                UserType.ADMIN.value,
                UserType.ROOT.value,
            }
        return obj.autor == self.request.user or self.request.user.get_tipo_usuario in {
            UserType.ADMIN.value,
            UserType.ROOT.value,
        }

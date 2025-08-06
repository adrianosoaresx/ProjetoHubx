from __future__ import annotations

from datetime import timedelta

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from .models import RespostaDiscussao, Tag, TopicoDiscussao
from .serializers import RespostaDiscussaoSerializer, TagSerializer, TopicoDiscussaoSerializer
from .services import marcar_resolucao, responder_topico
from .tasks import notificar_melhor_resposta, notificar_nova_resposta


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("nome")
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


@method_decorator(cache_page(60), name="list")
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
        search = self.request.query_params.get("search")
        if search:
            if connection.vendor == "postgresql":
                vector = (
                    SearchVector("titulo", weight="A")
                    + SearchVector("conteudo", weight="B")
                    + SearchVector("respostas__conteudo", weight="C")
                )
                query = SearchQuery(search)
                qs = (
                    qs.annotate(rank=SearchRank(vector, query))
                    .filter(rank__gt=0)
                    .order_by("-rank")
                )
            else:
                qs = qs.filter(
                    Q(titulo__icontains=search)
                    | Q(conteudo__icontains=search)
                    | Q(respostas__conteudo__icontains=search)
                ).distinct()
        tags_param = self.request.query_params.get("tags")
        if tags_param:
            names = [t.strip() for t in tags_param.split(",") if t.strip()]
            for name in names:
                qs = qs.filter(tags__nome=name)
        return qs

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
        cache.clear()

    def perform_update(self, serializer):
        if not self._can_edit(serializer.instance):
            raise PermissionDenied("Prazo de edição expirado.")
        serializer.save()
        cache.clear()

    def perform_destroy(self, instance):  # type: ignore[override]
        super().perform_destroy(instance)
        cache.clear()

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

    @action(detail=True, methods=["post"], url_path="marcar-resolvido")
    def marcar_resolvido(self, request, pk=None):
        topico = self.get_object()
        resposta_id = request.data.get("resposta_id")
        resposta = get_object_or_404(topico.respostas, id=resposta_id)
        marcar_resolucao(topico=topico, resposta=resposta, user=request.user)
        notificar_melhor_resposta.delay(resposta.id)
        cache.clear()
        serializer = self.get_serializer(topico)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="desmarcar-resolvido")
    def desmarcar_resolvido(self, request, pk=None):
        topico = self.get_object()
        if request.user not in {topico.autor} and request.user.get_tipo_usuario not in {
            UserType.ADMIN.value,
            UserType.ROOT.value,
        }:
            return Response(status=403)
        with transaction.atomic():
            topico.melhor_resposta = None
            topico.resolvido = False
            topico.save(update_fields=["melhor_resposta", "resolvido"])
        cache.clear()
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


@method_decorator(cache_page(60), name="list")
class RespostaViewSet(viewsets.ModelViewSet):
    queryset = RespostaDiscussao.objects.select_related("autor", "topico").all()
    serializer_class = RespostaDiscussaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            if connection.vendor == "postgresql":
                vector = SearchVector("conteudo", weight="A")
                query = SearchQuery(search)
                qs = qs.annotate(rank=SearchRank(vector, query)).filter(rank__gt=0).order_by("-rank")
            else:
                qs = qs.filter(conteudo__icontains=search)
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        resposta = responder_topico(
            topico=data["topico"],
            autor=self.request.user,
            conteudo=data["conteudo"],
            reply_to=data.get("reply_to"),
            arquivo=data.get("arquivo"),
        )
        serializer.instance = resposta
        notificar_nova_resposta.delay(resposta.id)
        cache.clear()

    def perform_update(self, serializer):
        if not self._can_edit(serializer.instance):
            raise PermissionDenied("Prazo de edição expirado.")
        serializer.save()
        cache.clear()

    def perform_destroy(self, instance):  # type: ignore[override]
        super().perform_destroy(instance)
        cache.clear()

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

from __future__ import annotations


from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from .cache_utils import (
    CATEGORIAS_LIST_KEY_PREFIX,
    TOPICOS_LIST_KEY_PREFIX,
    categorias_list_cache_key,
    topicos_list_cache_key,
)
from .models import (
    CategoriaDiscussao,
    Denuncia,
    InteracaoDiscussao,
    RespostaDiscussao,
    Tag,
    TopicoDiscussao,
)
from .permissions import publicos_permitidos
from .serializers import (
    CategoriaDiscussaoSerializer,
    DenunciaSerializer,
    RespostaDiscussaoSerializer,
    TagSerializer,
    TopicoDiscussaoSerializer,
    VotoDiscussaoSerializer,
)
from .services import marcar_resolucao, responder_topico, verificar_prazo_edicao
from .services.agenda_bridge import criar_reuniao as criar_reuniao_agenda
from .tasks import (
    notificar_melhor_resposta,
    notificar_nova_resposta,
    notificar_topico_resolvido,
)


@method_decorator(cache_page(60, key_prefix=CATEGORIAS_LIST_KEY_PREFIX), name="list")
class CategoriaDiscussaoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaDiscussao.objects.all().order_by("nome")
    serializer_class = CategoriaDiscussaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        org = self.request.query_params.get("organizacao")
        if org:
            qs = qs.filter(organizacao_id=org)
        nucleo = self.request.query_params.get("nucleo")
        if nucleo:
            qs = qs.filter(nucleo_id=nucleo)
        evento = self.request.query_params.get("evento")
        if evento:
            qs = qs.filter(evento_id=evento)
        return qs

    def perform_create(self, serializer):
        serializer.save()
        cache.delete(categorias_list_cache_key())

    def perform_update(self, serializer):
        serializer.save()
        cache.delete(categorias_list_cache_key())

    def perform_destroy(self, instance):  # type: ignore[override]
        super().perform_destroy(instance)
        cache.delete(categorias_list_cache_key())


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("nome")
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"


@method_decorator(cache_page(60, key_prefix=TOPICOS_LIST_KEY_PREFIX), name="list")
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
        qs = qs.filter(publico_alvo__in=publicos_permitidos(self.request.user.user_type))
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
        ordering = self.request.query_params.get("ordering")
        if ordering in {"score", "-score"}:
            qs = qs.annotate(score=Coalesce(Sum("interacoes__valor"), 0)).order_by(
                "-score" if ordering == "score" else "score"
            )
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.publico_alvo not in publicos_permitidos(request.user.user_type):
            raise PermissionDenied()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
        cache.delete(categorias_list_cache_key())
        cache.delete(topicos_list_cache_key(serializer.instance.categoria.slug))

    def perform_update(self, serializer):
        if not self._can_edit(serializer.instance):
            raise PermissionDenied("Prazo de edição expirado.")
        serializer.save()
        cache.delete(categorias_list_cache_key())
        cache.delete(topicos_list_cache_key(serializer.instance.categoria.slug))

    def perform_destroy(self, instance):  # type: ignore[override]
        if not verificar_prazo_edicao(instance, self.request.user):
            raise PermissionDenied("Prazo de exclusão expirado.")
        super().perform_destroy(instance)
        cache.delete(categorias_list_cache_key())
        cache.delete(topicos_list_cache_key(instance.categoria.slug))

    def _can_edit(self, obj: TopicoDiscussao) -> bool:
        return verificar_prazo_edicao(obj, self.request.user)

    @action(detail=True, methods=["post"], url_path="marcar-resolvido")
    def marcar_resolvido(self, request, pk=None):
        topico = self.get_object()
        resposta_id = request.data.get("resposta_id")
        resposta = get_object_or_404(topico.respostas, id=resposta_id)
        was_resolved = topico.resolvido
        topico = marcar_resolucao(topico=topico, resposta=resposta, user=request.user)
        notificar_melhor_resposta.delay(resposta.id)
        if not was_resolved:
            notificar_topico_resolvido.delay(topico.id)
        cache.delete(topicos_list_cache_key(topico.categoria.slug))
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
        cache.delete(topicos_list_cache_key(topico.categoria.slug))
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

    @action(detail=True, methods=["post"], url_path="criar-reuniao")
    def criar_reuniao(self, request, pk=None):
        topico = self.get_object()
        criar_reuniao_agenda(
            topico,
            request.data.get("data_inicio"),
            request.data.get("data_fim"),
            request.data.get("participantes", []),
        )
        return Response(status=204)


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
        try:
            resposta = responder_topico(
                topico=data["topico"],
                autor=self.request.user,
                conteudo=data["conteudo"],
                reply_to=data.get("reply_to"),
                arquivo=data.get("arquivo"),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        serializer.instance = resposta
        notificar_nova_resposta.delay(resposta.id)
        cache.delete(topicos_list_cache_key(resposta.topico.categoria.slug))

    def perform_update(self, serializer):
        if not self._can_edit(serializer.instance):
            raise PermissionDenied("Prazo de edição expirado.")
        serializer.save()
        cache.delete(topicos_list_cache_key(serializer.instance.topico.categoria.slug))

    def perform_destroy(self, instance):  # type: ignore[override]
        if not verificar_prazo_edicao(instance, self.request.user):
            raise PermissionDenied("Prazo de exclusão expirado.")
        super().perform_destroy(instance)
        cache.delete(topicos_list_cache_key(instance.topico.categoria.slug))

    def _can_edit(self, obj: RespostaDiscussao) -> bool:
        return verificar_prazo_edicao(obj, self.request.user)


class VotoDiscussaoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @method_decorator(
        ratelimit(key="user_or_ip", rate="20/m", method="POST", block=True)
    )
    def create(self, request):
        serializer = VotoDiscussaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ct = get_object_or_404(ContentType, id=serializer.validated_data["content_type_id"])
        obj = get_object_or_404(ct.model_class(), id=serializer.validated_data["object_id"])
        interacao, created = InteracaoDiscussao.objects.get_or_create(
            user=request.user,
            content_type=ct,
            object_id=obj.pk,
            defaults={"valor": serializer.validated_data["valor"]},
        )
        if not created:
            if interacao.valor == serializer.validated_data["valor"]:
                interacao.delete()
            else:
                interacao.valor = serializer.validated_data["valor"]
                interacao.save(update_fields=["valor"])
        if isinstance(obj, TopicoDiscussao):
            slug = obj.categoria.slug
        elif isinstance(obj, RespostaDiscussao):
            slug = obj.topico.categoria.slug
        else:
            slug = None
        if slug:
            cache.delete(topicos_list_cache_key(slug))
        return Response({"score": obj.score, "num_votos": obj.num_votos})


class DenunciaViewSet(viewsets.ModelViewSet):
    queryset = Denuncia.objects.select_related("log").all()
    serializer_class = DenunciaSerializer
    permission_classes = [IsAuthenticated]

    @method_decorator(
        ratelimit(key="user_or_ip", rate="20/m", method="POST", block=True)
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):  # pragma: no cover - simple filter
        qs = super().get_queryset()
        if self.request.user.get_tipo_usuario not in {
            UserType.ADMIN.value,
            UserType.ROOT.value,
        }:
            qs = qs.filter(user=self.request.user)
        return qs

    @action(detail=True, methods=["post"], url_path="aprovar")
    def aprovar(self, request, pk=None):
        if request.user.get_tipo_usuario not in {UserType.ADMIN.value, UserType.ROOT.value}:
            return Response(status=403)
        denuncia = self.get_object()
        notes = request.data.get("notes", "")
        denuncia.aprovar(request.user, notes)
        serializer = self.get_serializer(denuncia)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="rejeitar")
    def rejeitar(self, request, pk=None):
        if request.user.get_tipo_usuario not in {UserType.ADMIN.value, UserType.ROOT.value}:
            return Response(status=403)
        denuncia = self.get_object()
        notes = request.data.get("notes", "")
        denuncia.rejeitar(request.user, notes)
        serializer = self.get_serializer(denuncia)
        return Response(serializer.data)

from __future__ import annotations

from datetime import datetime

import boto3
from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.core.exceptions import ValidationError, ValidationError as DjangoValidationError
from django.core.files.storage import default_storage
from django.db import connection
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Comment, Like, ModeracaoPost, Post
from .tasks import POSTS_CREATED, notify_new_post, notify_post_moderated
from feed.application.denunciar_post import DenunciarPost


class CanModerate(permissions.BasePermission):
    def has_permission(self, request, view):  # pragma: no cover - simples
        return request.user.has_perm("feed.change_moderacaopost")


class PostSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "tipo_feed",
            "conteudo",
            "image",
            "pdf",
            "video",
            "image_url",
            "pdf_url",
            "video_url",
            "nucleo",
            "evento",
            "tags",
            "autor",
            "organizacao",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "autor", "organizacao", "created_at", "updated_at"]

    def validate(self, attrs):
        tipo_feed = attrs.get("tipo_feed") or getattr(self.instance, "tipo_feed", None)
        if tipo_feed == "nucleo" and not attrs.get("nucleo"):
            raise serializers.ValidationError({"nucleo": "Núcleo é obrigatório"})
        if tipo_feed == "evento" and not attrs.get("evento"):
            raise serializers.ValidationError({"evento": "Evento é obrigatório"})
        return attrs

    def validate_conteudo(self, value: str | None) -> str | None:
        if value and len(value) > 500:
            raise serializers.ValidationError("Conteúdo deve ter no máximo 500 caracteres.")
        return value

    def _handle_media(self, validated_data):
        from .services import upload_media

        for field in ["image", "pdf", "video"]:
            file = validated_data.get(field)
            if file:
                try:
                    validated_data[field] = upload_media(file)
                except DjangoValidationError as e:
                    raise serializers.ValidationError({field: e.messages}) from e

    def create(self, validated_data):
        self._handle_media(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._handle_media(validated_data)
        return super().update(instance, validated_data)

    def _generate_presigned(self, key: str | None) -> str | None:  # pragma: no cover - simples
        if not key:
            return None
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
        if bucket:
            client = boto3.client("s3")
            return client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
            )
        return default_storage.url(key)

    def get_image_url(self, obj: Post) -> str | None:  # pragma: no cover - simples
        key = getattr(obj.image, "name", obj.image)
        return self._generate_presigned(key)

    def get_pdf_url(self, obj: Post) -> str | None:  # pragma: no cover - simples
        key = getattr(obj.pdf, "name", obj.pdf)
        return self._generate_presigned(key)

    def get_video_url(self, obj: Post) -> str | None:  # pragma: no cover - simples
        key = getattr(obj.video, "name", obj.video)
        return self._generate_presigned(key)


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    cache_timeout = 60

    def get_queryset(self):
        qs = (
            Post.objects.select_related("autor", "organizacao", "nucleo", "evento", "moderacao")
            .prefetch_related("tags")
            .exclude(moderacao__status="rejeitado")
        )
        if not self.request.user.is_staff:
            qs = qs.filter(
                Q(moderacao__status="aprovado") | Q(autor=self.request.user)
            )
        qs = qs.distinct()
        params = self.request.query_params
        tipo_feed = params.get("tipo_feed")
        if tipo_feed:
            qs = qs.filter(tipo_feed=tipo_feed)
        organizacao = params.get("organizacao")
        if organizacao:
            qs = qs.filter(organizacao_id=organizacao)
        nucleo = params.get("nucleo")
        if nucleo:
            qs = qs.filter(nucleo_id=nucleo)
        evento = params.get("evento")
        if evento:
            qs = qs.filter(evento_id=evento)
        tags = params.get("tags")
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            qs = qs.filter(Q(tags__id__in=tag_list) | Q(tags__nome__in=tag_list)).distinct()
        date_from = params.get("date_from")
        if date_from:
            try:
                qs = qs.filter(created_at__date__gte=datetime.fromisoformat(date_from).date())
            except ValueError:
                pass
        date_to = params.get("date_to")
        if date_to:
            try:
                qs = qs.filter(created_at__date__lte=datetime.fromisoformat(date_to).date())
            except ValueError:
                pass
        q = params.get("q")
        if q:
            or_terms = [t.strip() for t in q.split("|") if t.strip()]
            if connection.vendor == "postgresql":
                query_parts = [" & ".join(term.split()) for term in or_terms]
                query = SearchQuery(" | ".join(query_parts), config="portuguese")
                vector = (
                    SearchVector("conteudo", config="portuguese")
                    + SearchVector("tags__nome", config="portuguese")
                )
                return (
                    qs.annotate(search=vector, rank=SearchRank(vector, query))
                    .filter(search=query)
                    .order_by("-rank")
                )
            or_query = Q()
            for term in or_terms:
                sub = Q()
                for part in term.split():
                    sub &= Q(conteudo__icontains=part) | Q(tags__nome__icontains=part)
                or_query |= sub
            return qs.filter(or_query)
        return qs.order_by("-created_at")

    def _cache_key(self, request) -> str:
        params = request.query_params
        keys = [
            str(request.user.pk),
            *(params.get(k, "") for k in [
                "tipo_feed",
                "organizacao",
                "nucleo",
                "evento",
                "tags",
                "page",
                "q",
            ]),
        ]
        return "feed:api:" + ":".join(keys)

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        key = self._cache_key(request)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data, self.cache_timeout)
        return response

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        post = serializer.save(autor=self.request.user, organizacao=self.request.user.organizacao)
        POSTS_CREATED.inc()
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notify_new_post(post.id)
        else:
            notify_new_post.delay(post.id)

    def perform_destroy(self, instance: Post) -> None:
        instance.soft_delete()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def flag(self, request, pk=None):
        post = self.get_object()
        use_case = DenunciarPost()
        try:
            use_case.execute(post=post, user=request.user)
        except ValidationError as e:
            return Response({"detail": e.message}, status=400)
        return Response(status=204)

    @action(detail=True, methods=["post"], permission_classes=[CanModerate])
    def moderate(self, request, pk=None):
        post = self.get_object()
        serializer = ModeracaoPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        moderacao, _ = ModeracaoPost.objects.update_or_create(
            post=post,
            defaults={
                "status": serializer.validated_data["status"],
                "motivo": serializer.validated_data.get("motivo", ""),
                "avaliado_por": request.user,
                "avaliado_em": timezone.now(),
            },
        )
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notify_post_moderated(str(post.id), moderacao.status)
        else:
            notify_post_moderated.delay(str(post.id), moderacao.status)
        return Response(ModeracaoPostSerializer(moderacao).data)


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "post", "user", "reply_to", "texto", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Comment.objects.select_related("post", "user").all()

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        serializer.save(user=self.request.user)


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ["id", "post", "user", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class LikeViewSet(viewsets.ModelViewSet):
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Like.objects.select_related("post", "user").all()

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        serializer.save(user=self.request.user)


class ModeracaoPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeracaoPost
        fields = [
            "id",
            "post",
            "status",
            "motivo",
            "avaliado_por",
            "avaliado_em",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "post", "avaliado_por", "avaliado_em", "created_at", "updated_at"]


class ModeracaoPostViewSet(viewsets.ModelViewSet):
    serializer_class = ModeracaoPostSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = ModeracaoPost.objects.select_related("post", "avaliado_por").all()

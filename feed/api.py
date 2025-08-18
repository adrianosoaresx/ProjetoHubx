from __future__ import annotations

import re
from datetime import datetime
from math import ceil

import boto3
from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.storage import default_storage
from django.db import connection
from django.db.models import Count, Q, OuterRef, Subquery
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_ratelimit.core import is_ratelimited
from prometheus_client import Counter, Histogram
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from feed.application.denunciar_post import DenunciarPost
from feed.application.moderar_ai import aplicar_decisao, pre_analise

from .models import Bookmark, Comment, Like, ModeracaoPost, Post, PostView, Reacao, Tag
from .tasks import POSTS_CREATED, notify_new_post, notify_post_moderated

REACTIONS_TOTAL = Counter(
    "feed_reactions_total", "Total de reações registradas", ["vote"]
)
POST_VIEWS_TOTAL = Counter(
    "feed_post_views_total", "Total de visualizações de posts"
)
POST_VIEW_DURATION = Histogram(
    "feed_post_view_duration_seconds", "Tempo de leitura dos posts em segundos"
)


class CanModerate(permissions.BasePermission):
    def has_permission(self, request, view):  # pragma: no cover - simples
        return request.user.has_perm("feed.change_moderacaopost")



class IsCommentAuthorOrModerator(permissions.BasePermission):
    """Permite edição apenas ao autor do comentário ou a moderadores."""

    message = "Apenas o autor ou moderadores podem modificar o comentário."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user_id == request.user.id or request.user.is_staff


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "nome"]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("nome")
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

class CanEditPost(permissions.BasePermission):
    """Permite edição apenas ao autor ou a quem possui ``feed.change_post``."""

    def has_object_permission(self, request, view, obj):
        return obj.autor == request.user or request.user.has_perm("feed.change_post")




class PostSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    video_preview_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "tipo_feed",
            "conteudo",
            "image",
            "pdf",
            "video",
            "video_preview",
            "image_url",
            "pdf_url",
            "video_url",
            "video_preview_url",
            "nucleo",
            "evento",
            "tags",
            "autor",
            "organizacao",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "autor", "organizacao", "created_at", "updated_at", "video_preview"]

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
                    result = upload_media(file)
                except DjangoValidationError as e:
                    raise serializers.ValidationError({field: e.messages}) from e
                if field == "video" and isinstance(result, tuple):
                    validated_data["video"], validated_data["video_preview"] = result
                else:
                    validated_data[field] = result

    def create(self, validated_data):
        self._handle_media(validated_data)
        decision = pre_analise(validated_data.get("conteudo", ""))
        if decision == "rejeitado":
            raise serializers.ValidationError({"conteudo": "Conteúdo não permitido."})
        post = super().create(validated_data)
        aplicar_decisao(post, decision)
        return post

    def update(self, instance, validated_data):
        self._handle_media(validated_data)
        decision = pre_analise(validated_data.get("conteudo", instance.conteudo or ""))
        if decision == "rejeitado":
            raise serializers.ValidationError({"conteudo": "Conteúdo não permitido."})
        post = super().update(instance, validated_data)
        aplicar_decisao(post, decision)
        return post

    def _generate_presigned(self, key: str | None) -> str | None:  # pragma: no cover - simples
        if not key:
            return None
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
        if bucket:
            client = boto3.client("s3")
            return client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
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

    def get_video_preview_url(self, obj: Post) -> str | None:  # pragma: no cover - simples
        key = getattr(obj.video_preview, "name", obj.video_preview)
        return self._generate_presigned(key)


class NucleoPostSerializer(PostSerializer):
    """Serializer específico para posts de núcleo."""

    class Meta(PostSerializer.Meta):
        fields = [f for f in PostSerializer.Meta.fields if f not in {"tipo_feed", "nucleo", "evento"}]
        read_only_fields = PostSerializer.Meta.read_only_fields

    def validate(self, attrs):
        attrs["tipo_feed"] = "nucleo"
        attrs["nucleo"] = self.context["nucleo"]
        return super().validate(attrs)


def _rate_with_multiplier(base: str, multiplier: float) -> str:
    match = re.match(r"(\d+)/(\w+)", base)
    if not match:
        return base
    count, period = match.groups()
    count = max(1, ceil(int(count) * multiplier))
    return f"{count}/{period}"


def _post_rate(group, request) -> str:  # pragma: no cover - simples
    mult = getattr(getattr(request.user, "organizacao", None), "rate_limit_multiplier", 1)
    return _rate_with_multiplier(settings.FEED_RATE_LIMIT_POST, mult)


def _read_rate(group, request) -> str:  # pragma: no cover - simples
    mult = getattr(getattr(request.user, "organizacao", None), "rate_limit_multiplier", 1)
    return _rate_with_multiplier(settings.FEED_RATE_LIMIT_READ, mult)


def ratelimit_exceeded(request, exception):  # pragma: no cover - simples
    return Response(
        {"detail": _("Limite de requisições excedido.")},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    cache_timeout = 60

    def get_permissions(self):  # pragma: no cover - simples
        perms = super().get_permissions()
        if self.action in {"update", "partial_update", "destroy"}:
            perms.append(CanEditPost())
        return perms

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        if is_ratelimited(
            request,
            group="feed_posts_create",
            key="user",
            rate=_post_rate(None, request),
            method="POST",
            increment=True,
        ):
            return ratelimit_exceeded(request, None)
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        latest_status = ModeracaoPost.objects.filter(post=OuterRef("pk")).order_by("-created_at").values("status")[:1]
        qs = (
            Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
            .prefetch_related("tags")
            .annotate(mod_status=Subquery(latest_status))
            .exclude(mod_status="rejeitado")
        )
        if not self.request.user.is_staff:
            qs = qs.filter(Q(mod_status="aprovado") | Q(autor=self.request.user))
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
            qs = qs.filter(
                Q(tags__id__in=tag_list) | Q(tags__nome__in=tag_list),
                tags__deleted=False,
            ).distinct()
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
                vector = SearchVector("conteudo", config="portuguese") + SearchVector("tags__nome", config="portuguese")
                return (
                    qs.annotate(search=vector, rank=SearchRank(vector, query))
                    .filter(search=query)
                    .filter(Q(tags__deleted=False) | Q(tags__isnull=True))
                    .order_by("-rank")
                )
            or_query = Q()
            for term in or_terms:
                sub = Q()
                for part in term.split():
                    sub &= Q(conteudo__icontains=part) | Q(tags__nome__icontains=part, tags__deleted=False)
                or_query |= sub
            return qs.filter(or_query)
        return qs.order_by("-created_at")

    def _cache_key(self, request) -> str:
        params = request.query_params
        keys = [
            str(request.user.pk),
            *(
                params.get(k, "")
                for k in [
                    "tipo_feed",
                    "organizacao",
                    "nucleo",
                    "evento",
                    "tags",
                    "page",
                    "q",
                ]
            ),
        ]
        return "feed:api:" + ":".join(keys)

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        if is_ratelimited(
            request,
            group="feed_posts_list",
            key="user",
            rate=_read_rate(None, request),
            method="GET",
            increment=True,
        ):
            return ratelimit_exceeded(request, None)
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
    def bookmark(self, request, pk=None):
        post = self.get_object()
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            return Response({"bookmarked": False}, status=status.HTTP_200_OK)
        return Response({"bookmarked": True}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def toggle_like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)
        return Response({"liked": True}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def flag(self, request, pk=None):
        post = self.get_object()
        use_case = DenunciarPost()
        try:
            use_case.execute(post=post, user=request.user)
        except ValidationError as e:
            return Response({"detail": e.message}, status=400)
        return Response(status=204)

    @action(detail=True, methods=["post"], permission_classes=[CanModerate], url_path="avaliar")
    def moderate(self, request, pk=None):
        post = self.get_object()
        serializer = ModeracaoPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        moderacao = ModeracaoPost.objects.create(
            post=post,
            status=serializer.validated_data["status"],
            motivo=serializer.validated_data.get("motivo", ""),
            avaliado_por=request.user,
            avaliado_em=timezone.now(),
        )
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notify_post_moderated(str(post.id), moderacao.status)
        else:
            notify_post_moderated.delay(str(post.id), moderacao.status)
        return Response(ModeracaoPostSerializer(moderacao).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="reacoes",
        permission_classes=[permissions.IsAuthenticated],
    )
    def add_reaction(self, request, pk=None):
        post = self.get_object()
        vote = request.data.get("vote")
        if vote not in Reacao.Tipo.values:
            return Response({"detail": "Voto inválido."}, status=status.HTTP_400_BAD_REQUEST)
        if is_ratelimited(
            request,
            group="feed_reactions_create",
            key="user",
            rate=_read_rate(None, request),
            method="POST",
            increment=True,
        ):
            return ratelimit_exceeded(request, None)
        reacao, created = Reacao.all_objects.get_or_create(
            post=post, user=request.user, vote=vote
        )
        if created or reacao.deleted:
            reacao.deleted = False
            reacao.save(update_fields=["deleted"])
            REACTIONS_TOTAL.labels(vote=vote).inc()
            cache.delete(f"post_reacoes:{post.id}")
            return Response({"vote": vote}, status=status.HTTP_201_CREATED)
        return Response({"vote": vote}, status=status.HTTP_200_OK)

    @add_reaction.mapping.get
    def list_reactions(self, request, pk=None):
        post = self.get_object()
        cache_key = f"post_reacoes:{post.id}"
        data = cache.get(cache_key)
        if data is None:
            counts = (
                Reacao.objects.filter(post=post, deleted=False)
                .values("vote")
                .annotate(count=Count("id"))
            )
            data = {c["vote"]: c["count"] for c in counts}
            cache.set(cache_key, data, self.cache_timeout)
        user_reaction = None
        if request.user.is_authenticated:
            user_reaction = (
                Reacao.objects.filter(
                    post=post, user=request.user, deleted=False
                )
                .values_list("vote", flat=True)
                .first()
            )
        data = {**{"like": 0, "share": 0}, **data, "user_reaction": user_reaction}
        return Response(data)

    @action(
        detail=True,
        methods=["delete"],
        url_path="reacoes/(?P<vote>[^/.]+)",
        permission_classes=[permissions.IsAuthenticated],
    )
    def remove_reaction(self, request, pk=None, vote=None):
        post = self.get_object()
        qs = Reacao.objects.filter(
            post=post, user=request.user, vote=vote, deleted=False
        )
        if qs.exists():
            qs.update(deleted=True)
            cache.delete(f"post_reacoes:{post.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        url_path="views/open",
        permission_classes=[permissions.IsAuthenticated],
    )
    def open_view(self, request, pk=None):
        post = self.get_object()
        PostView.objects.create(
            post=post, user=request.user, opened_at=timezone.now()
        )
        POST_VIEWS_TOTAL.inc()
        return Response(status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="views/close",
        permission_classes=[permissions.IsAuthenticated],
    )
    def close_view(self, request, pk=None):
        post = self.get_object()
        view = (
            PostView.objects.filter(
                post=post, user=request.user, closed_at__isnull=True
            )
            .order_by("-opened_at")
            .first()
        )
        if not view:
            return Response(status=status.HTTP_404_NOT_FOUND)
        view.closed_at = timezone.now()
        view.save(update_fields=["closed_at"])
        duration = (view.closed_at - view.opened_at).total_seconds()
        POST_VIEW_DURATION.observe(duration)
        return Response({"tempo_leitura": duration})


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "post", "user", "reply_to", "texto", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCommentAuthorOrModerator]
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

    def get_queryset(self):  # pragma: no cover - simples
        return Like.objects.select_related("post", "user").filter(user=self.request.user)

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        serializer.save(user=self.request.user)


class BookmarkSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ["id", "post", "created_at", "updated_at"]
        read_only_fields = ["id", "post", "created_at", "updated_at"]


class BookmarkViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # pragma: no cover - simples
        return Bookmark.objects.filter(user=self.request.user).select_related("post")


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

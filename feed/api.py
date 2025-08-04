from __future__ import annotations

from datetime import datetime

from django.db.models import Q
from rest_framework import permissions, serializers, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import Comment, Like, ModeracaoPost, Post


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

    def _handle_media(self, validated_data):
        from .services import upload_media

        for field in ["image", "pdf", "video"]:
            file = validated_data.get(field)
            if file:
                validated_data[field] = upload_media(file)

    def create(self, validated_data):
        self._handle_media(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._handle_media(validated_data)
        return super().update(instance, validated_data)

    def get_image_url(self, obj: Post) -> str | None:  # pragma: no cover - simples
        if not obj.image:
            return None
        return obj.image if isinstance(obj.image, str) else obj.image.url

    def get_pdf_url(self, obj: Post) -> str | None:  # pragma: no cover - simples
        if not obj.pdf:
            return None
        return obj.pdf if isinstance(obj.pdf, str) else obj.pdf.url

    def get_video_url(self, obj: Post) -> str | None:  # pragma: no cover - simples
        if not obj.video:
            return None
        return obj.video if isinstance(obj.video, str) else obj.video.url


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        qs = (
            Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
            .prefetch_related("tags")
            .filter(Q(moderacoes__status="aprovado") | Q(moderacoes__isnull=True))
            .distinct()
        )
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
            qs = qs.filter(Q(conteudo__icontains=q) | Q(tags__nome__icontains=q)).distinct()
        return qs.order_by("-created_at")

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        serializer.save(autor=self.request.user, organizacao=self.request.user.organizacao)

    def perform_destroy(self, instance: Post) -> None:
        instance.soft_delete()


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
        read_only_fields = ["id", "created_at", "updated_at"]


class ModeracaoPostViewSet(viewsets.ModelViewSet):
    serializer_class = ModeracaoPostSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ModeracaoPost.objects.select_related("post", "avaliado_por").all()

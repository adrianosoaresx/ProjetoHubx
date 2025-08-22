from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models

from core.models import SoftDeleteManager, SoftDeleteModel, TimeStampedModel

User = get_user_model()


class Tag(TimeStampedModel, SoftDeleteModel):

    nome = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        unique_together = ("nome", "deleted")

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome


class FeedPluginConfig(TimeStampedModel):
    """Configuração de plugins para organizações."""

    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="feed_plugins",
    )
    module_path = models.CharField(max_length=255)
    frequency = models.PositiveIntegerField(default=0)
    last_run = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Configuração de Plugin"
        verbose_name_plural = "Configurações de Plugins"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.organizacao}: {self.module_path}"


class Post(TimeStampedModel, SoftDeleteModel):
    TIPO_FEED_CHOICES = [
        ("global", "Feed Global"),
        ("usuario", "Mural do Usuário"),
        ("nucleo", "Feed do Núcleo"),
        ("evento", "Feed do Evento"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    organizacao = models.ForeignKey("organizacoes.Organizacao", on_delete=models.CASCADE, related_name="posts")
    tipo_feed = models.CharField(max_length=10, choices=TIPO_FEED_CHOICES, default="global")
    conteudo = models.TextField(blank=True, validators=[MaxLengthValidator(500)])
    image = models.ImageField(upload_to="uploads/", null=True, blank=True)
    pdf = models.FileField(upload_to="uploads/", null=True, blank=True)
    video = models.FileField(upload_to="videos/", null=True, blank=True)
    video_preview = models.ImageField(upload_to="video_previews/", null=True, blank=True)
    nucleo = models.ForeignKey("nucleos.Nucleo", null=True, blank=True, on_delete=models.SET_NULL)
    evento = models.ForeignKey("agenda.Evento", null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def clean(self) -> None:
        super().clean()
        if self.tipo_feed == "nucleo" and not self.nucleo:
            raise ValidationError({"nucleo": "Núcleo é obrigatório"})
        if self.tipo_feed == "evento" and not self.evento:
            raise ValidationError({"evento": "Evento é obrigatório"})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            ModeracaoPost.objects.create(post=self)
        banned = getattr(settings, "FEED_BAD_WORDS", [])
        if any(bad.lower() in (self.conteudo or "").lower() for bad in banned):
            mod = self.moderacao
            if not mod or mod.status != "pendente":
                ModeracaoPost.objects.create(post=self, status="pendente")

    @property
    def moderacao(self):
        return self.moderacoes.order_by("-created_at").first()


class Like(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("post", "user", "deleted")
        verbose_name = "Curtida"
        verbose_name_plural = "Curtidas"


class Flag(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="flags")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="flags")

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("post", "user", "deleted")
        verbose_name = "Denúncia"
        verbose_name_plural = "Denúncias"


class Bookmark(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("user", "post", "deleted")
        verbose_name = "Bookmark"
        verbose_name_plural = "Bookmarks"


class Comment(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    reply_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    texto = models.TextField()

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Comentário"
        verbose_name_plural = "Comentários"


class ModeracaoPost(TimeStampedModel):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("rejeitado", "Rejeitado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="moderacoes")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    motivo = models.TextField(blank=True)
    avaliado_por = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
    )
    avaliado_em = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Moderação de Post"
        verbose_name_plural = "Moderações de Posts"


class Reacao(TimeStampedModel, SoftDeleteModel):
    """Registra curtidas e compartilhamentos em posts."""

    class Tipo(models.TextChoices):
        CURTIDA = "like", "Curtida"
        COMPARTILHAMENTO = "share", "Compartilhamento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reacoes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reacoes")
    vote = models.CharField(max_length=20, choices=Tipo.choices)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("post", "user", "vote", "deleted")
        verbose_name = "Reação"
        verbose_name_plural = "Reações"


class PostView(TimeStampedModel):
    """Registra tempos de leitura de posts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="visualizacoes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="visualizacoes")
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        verbose_name = "Visualização de Post"
        verbose_name_plural = "Visualizações de Posts"

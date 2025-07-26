from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel

User = get_user_model()


class Tag(TimeStampedModel):
    nome = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome


class Post(TimeStampedModel):
    TIPO_FEED_CHOICES = [
        ("global", "Feed Global"),
        ("usuario", "Mural do Usuário"),
        ("nucleo", "Feed do Núcleo"),
        ("evento", "Feed do Evento"),
    ]

    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    organizacao = models.ForeignKey("organizacoes.Organizacao", on_delete=models.CASCADE, related_name="posts")
    tipo_feed = models.CharField(max_length=10, choices=TIPO_FEED_CHOICES, default="global")
    conteudo = models.TextField(blank=True)
    image = models.ImageField(upload_to="uploads/", null=True, blank=True)
    pdf = models.FileField(upload_to="uploads/", null=True, blank=True)
    video = models.FileField(upload_to="uploads/", null=True, blank=True)
    nucleo = models.ForeignKey("nucleos.Nucleo", null=True, blank=True, on_delete=models.SET_NULL)
    evento = models.ForeignKey("agenda.Evento", null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def clean(self) -> None:
        super().clean()
        if self.video:
            ext = Path(self.video.name).suffix.lower()
            allowed = getattr(settings, "FEED_VIDEO_ALLOWED_EXTS", [".mp4", ".webm"])
            if ext not in allowed:
                raise ValidationError({"video": "Formato de vídeo não suportado"})
            max_size = getattr(settings, "FEED_VIDEO_MAX_SIZE", 50 * 1024 * 1024)
            if self.video.size > max_size:
                raise ValidationError({"video": "Vídeo maior que o limite"})


class Like(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        unique_together = ("post", "user")
        verbose_name = "Curtida"
        verbose_name_plural = "Curtidas"


class Comment(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    reply_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    texto = models.TextField()

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Comentário"
        verbose_name_plural = "Comentários"

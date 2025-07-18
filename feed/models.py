from django.contrib.auth import get_user_model
from django.db import models

from core.models import TimeStampedModel

User = get_user_model()


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
    nucleo = models.ForeignKey("nucleos.Nucleo", null=True, blank=True, on_delete=models.SET_NULL)
    evento = models.ForeignKey("agenda.Evento", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"


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

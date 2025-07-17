
from django.db import models
from model_utils.models import TimeStampedModel


class Post(TimeStampedModel):
    TIPO_FEED_CHOICES = [
        ("global", "Feed Global"),
        ("usuario", "Mural do Usuário"),
        ("nucleo", "Feed do Núcleo"),
        ("evento", "Feed do Evento"),
    ]

    autor = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="posts"
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="posts"
    )
    tipo_feed = models.CharField(
        max_length=10,
        choices=TIPO_FEED_CHOICES,
        default="global"
    )
    conteudo = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="uploads/",
        blank=True,
        null=True
    )
    pdf = models.FileField(
        upload_to="uploads/",
        blank=True,
        null=True
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="postagens"
    )
    evento = models.ForeignKey(
        "eventos.Evento",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="postagens"
    )

    class Meta:
        ordering = ["-created"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def __str__(self):
        return f"Post de {self.autor} ({self.tipo_feed})"

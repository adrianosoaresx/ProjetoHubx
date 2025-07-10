from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Post(models.Model):
    PUBLICO = "publico"
    NUCLEO = "nucleo"

    TIPO_FEED_CHOICES = [
        (PUBLICO, "Público"),
        (NUCLEO, "Núcleo"),
    ]

    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    conteudo = models.TextField(blank=True)
    media = models.FileField(
        upload_to="feed/media/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Mídia",
    )
    tipo_feed = models.CharField(
        max_length=10,
        choices=TIPO_FEED_CHOICES,
        default=PUBLICO,
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        on_delete=models.SET_NULL,
        related_name="posts",
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):  # pragma: no cover - simples
        return f"Post de {self.autor.username} em {self.criado_em:%d/%m/%Y}"

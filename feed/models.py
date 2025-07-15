from django.contrib.auth import get_user_model
from django.db import models

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
    image = models.ImageField(
        upload_to="uploads/",
        blank=True,
        null=True,
    )
    pdf = models.FileField(
        upload_to="uploads/",
        blank=True,
        null=True,
    )
    publico = models.BooleanField(default=True)
    tipo_feed = models.CharField(
        max_length=10,
        choices=TIPO_FEED_CHOICES,
        default=PUBLICO,
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="postagens",
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="posts",
        null=True,
        blank=True,
        db_column="organization",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):  # pragma: no cover - simples
        return f"Post de {self.autor.username} em {self.criado_em:%d/%m/%Y}"

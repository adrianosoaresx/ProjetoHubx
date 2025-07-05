from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Post(models.Model):
    class Visibilidade(models.TextChoices):
        PUBLICO = "publico", "público"
        CONEXOES = "conexoes", "conexões"
        PRIVADO = "privado", "privado"

    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    conteudo = models.TextField(blank=True)
    imagem = models.ImageField(upload_to="posts/", blank=True, null=True)
    visibilidade = models.CharField(
        max_length=10,
        choices=Visibilidade.choices,
        default=Visibilidade.PUBLICO,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):  # pragma: no cover - simples
        return f"Post de {self.autor.username} em {self.criado_em:%d/%m/%Y}"


from django.db import models
from django.contrib.auth import get_user_model
from core.models import TimeStampedModel

User = get_user_model()

class Categoria(TimeStampedModel):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="categorias",
        db_column="organization",
    )

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Topico(TimeStampedModel):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, related_name="topicos"
    )
    autor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="topicos_criados"
    )
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="topicos",
        db_column="organization",
    )

    class Meta:
        verbose_name = "Tópico"
        verbose_name_plural = "Tópicos"
        ordering = ["-created_at"]

    def __str__(self):
        return self.titulo


class Resposta(TimeStampedModel):
    topico = models.ForeignKey(
        Topico, on_delete=models.CASCADE, related_name="respostas"
    )
    autor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="respostas_criadas"
    )
    conteudo = models.TextField()

    class Meta:
        verbose_name = "Resposta"
        verbose_name_plural = "Respostas"
        ordering = ["created_at"]

    def __str__(self):
        return f"Resposta por {self.autor.username} em {self.topico.titulo}"

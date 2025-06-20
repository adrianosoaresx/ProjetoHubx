from django.db import models
from django.contrib.auth import get_user_model
from organizacoes.models import Organizacao

User = get_user_model()


class Nucleo(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE, related_name="nucleos")
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="nucleos/avatars/", blank=True, null=True)
    data_criacao = models.DateField(auto_now_add=True)
    membros = models.ManyToManyField(User, related_name="nucleos", blank=True)

    class Meta:
        verbose_name = "Núcleo"
        verbose_name_plural = "Núcleos"

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome

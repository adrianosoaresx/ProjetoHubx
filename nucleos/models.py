from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import SET_NULL
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import SoftDeleteModel, TimeStampedModel

User = get_user_model()


class ParticipacaoNucleo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="participacoes")
    nucleo = models.ForeignKey("Nucleo", on_delete=models.CASCADE, related_name="participacoes")
    is_coordenador = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=[
            ("pendente", _("Pendente")),
            ("aprovado", _("Aprovado")),
            ("recusado", _("Recusado")),
        ],
        default="pendente",
    )
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_decisao = models.DateTimeField(null=True, blank=True)
    decidido_por = models.ForeignKey(
        User,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="decisoes_participacao",
    )

    class Meta:
        unique_together = ("user", "nucleo")
        verbose_name = "Participação no Núcleo"
        verbose_name_plural = "Participações nos Núcleos"


class Nucleo(TimeStampedModel, SoftDeleteModel):
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="nucleos",
        db_column="organizacao",
    )
    nome = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, default=uuid.uuid4)
    descricao = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="nucleos/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="nucleos/capas/", blank=True, null=True)
    membros = models.ManyToManyField(
        User,
        through="ParticipacaoNucleo",
        through_fields=("nucleo", "user"),
        related_name="nucleos",
    )
    data_criacao = models.DateField(auto_now_add=True)
    deleted = models.BooleanField(default=False)
    inativa = models.BooleanField(default=False)
    inativada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Núcleo"
        verbose_name_plural = "Núcleos"

    def __str__(self) -> str:
        return self.nome

    @property
    def membros_aprovados(self):
        """Retorna apenas os usuários com participação aprovada."""
        return self.membros.filter(participacoes__status="aprovado")

    @property
    def coordenadores(self):
        return self.membros.filter(participacoes__status="aprovado", participacoes__is_coordenador=True)

    def soft_delete(self) -> None:
        self.delete()

    def delete(
        self, using: str | None = None, keep_parents: bool = False, soft: bool = True
    ) -> None:
        if soft:
            self.deleted = True
            self.save(update_fields=["deleted"])
        super().delete(using=using, keep_parents=keep_parents, soft=soft)

    def save(self, *args, **kwargs):
        if self.slug:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)


class CoordenadorSuplente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nucleo = models.ForeignKey(
        Nucleo,
        on_delete=models.CASCADE,
        related_name="coordenadores_suplentes",
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="suplencias",
    )
    periodo_inicio = models.DateTimeField()
    periodo_fim = models.DateTimeField()

    class Meta:
        verbose_name = "Coordenador Suplente"
        verbose_name_plural = "Coordenadores Suplentes"

from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import SET_NULL
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from core.models import SoftDeleteModel, TimeStampedModel

User = get_user_model()


class ParticipacaoNucleo(TimeStampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="participacoes")
    nucleo = models.ForeignKey("Nucleo", on_delete=models.CASCADE, related_name="participacoes")

    PAPEL_CHOICES = [("membro", _("Membro")), ("coordenador", _("Coordenador"))]
    papel = models.CharField(max_length=20, choices=PAPEL_CHOICES, default="membro")

    STATUS_CHOICES = [
        ("pendente", _("Pendente")),
        ("ativo", _("Ativo")),
        ("inativo", _("Inativo")),
        ("suspenso", _("Suspenso")),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente",
        db_index=True,
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
    justificativa = models.TextField(blank=True)

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
    slug = models.SlugField(max_length=255, blank=True)
    descricao = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="nucleos/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="nucleos/capas/", blank=True, null=True)
    ativo = models.BooleanField(default=True)
    mensalidade = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("30.00"))

    class Meta:
        unique_together = ("organizacao", "slug")
        verbose_name = "Núcleo"
        verbose_name_plural = "Núcleos"

    def __str__(self) -> str:
        return self.nome

    @property
    def membros(self):
        return User.objects.filter(
            participacoes__nucleo=self, participacoes__status="ativo"
        )

    @property
    def coordenadores(self):
        return self.membros.filter(participacoes__papel="coordenador")

    def soft_delete(self) -> None:
        self.deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted", "deleted_at"])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        else:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)


class CoordenadorSuplente(TimeStampedModel, SoftDeleteModel):
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
    periodo_inicio = models.DateTimeField(db_index=True)
    periodo_fim = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = "Coordenador Suplente"
        verbose_name_plural = "Coordenadores Suplentes"

    @property
    def ativo(self) -> bool:
        now = timezone.now()
        return self.periodo_inicio <= now <= self.periodo_fim


class ConviteNucleo(models.Model):
    token = models.CharField(max_length=36, unique=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    papel = models.CharField(
        max_length=20,
        choices=[("membro", "Membro"), ("coordenador", "Coordenador")],
    )
    usado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    nucleo = models.ForeignKey(Nucleo, on_delete=models.CASCADE)

    def expirado(self) -> bool:
        from django.conf import settings
        from datetime import timedelta

        dias = getattr(settings, "CONVITE_NUCLEO_EXPIRACAO_DIAS", 7)
        return self.criado_em + timedelta(days=dias) < timezone.now()

    class Meta:
        verbose_name = "Convite para Núcleo"
        verbose_name_plural = "Convites para Núcleos"

from __future__ import annotations

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import SET_NULL
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

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
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente",
        db_index=True,
    )
    status_suspensao = models.BooleanField(default=False)
    data_suspensao = models.DateTimeField(null=True, blank=True)
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
    mensalidade = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("30.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("organizacao", "slug"), name="uniq_org_slug")
        ]
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


class ConviteNucleo(TimeStampedModel, SoftDeleteModel):
    token = models.CharField(max_length=36, unique=True, default=uuid.uuid4, editable=False)
    token_obj = models.ForeignKey(
        "tokens.TokenAcesso",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="convites_nucleo",
        db_column="token_id",
    )
    email = models.EmailField()
    papel = models.CharField(
        max_length=20,
        choices=[("membro", "Membro"), ("coordenador", "Coordenador")],
    )
    limite_uso_diario = models.PositiveSmallIntegerField(default=1)
    data_expiracao = models.DateTimeField(null=True, blank=True)
    usado_em = models.DateTimeField(null=True, blank=True)
    nucleo = models.ForeignKey(Nucleo, on_delete=models.CASCADE)

    def expirado(self) -> bool:
        if self.data_expiracao:
            return self.data_expiracao < timezone.now()
        from datetime import timedelta

        from django.conf import settings

        dias = getattr(settings, "CONVITE_NUCLEO_EXPIRACAO_DIAS", 7)
        return self.created_at + timedelta(days=dias) < timezone.now()

    class Meta:
        verbose_name = "Convite para Núcleo"
        verbose_name_plural = "Convites para Núcleos"

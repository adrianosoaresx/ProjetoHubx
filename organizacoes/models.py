import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel as ExtTimeStampedModel

from core.models import SoftDeleteModel, TimeStampedModel


class Organizacao(TimeStampedModel, SoftDeleteModel):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    descricao = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    tipo = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=[
            ("ong", _("ONG")),
            ("empresa", _("Empresa")),
            ("coletivo", _("Coletivo")),
        ],
        blank=True,
    )
    rua = models.CharField(_("Rua"), max_length=255, blank=True)
    cidade = models.CharField(_("Cidade"), max_length=100, blank=True)
    estado = models.CharField(_("Estado"), max_length=50, blank=True)
    contato_nome = models.CharField(_("Contato principal"), max_length=255, blank=True)
    contato_email = models.EmailField(_("Email do contato"), blank=True)
    contato_telefone = models.CharField(_("Telefone do contato"), max_length=20, blank=True)
    avatar = models.ImageField(upload_to="organizacoes/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="organizacoes/capas/", blank=True, null=True)
    deleted = models.BooleanField(default=False)
    inativa = models.BooleanField(default=False)
    inativada_em = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organizacoes_criadas",
    )

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    def delete(
        self, using: str | None = None, keep_parents: bool = False, soft: bool = True
    ) -> None:
        if soft:
            self.deleted = True
            self.save(update_fields=["deleted"])
        super().delete(using=using, keep_parents=keep_parents, soft=soft)


class OrganizacaoLog(ExtTimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    acao = models.CharField(max_length=50)
    dados_antigos = models.JSONField(default=dict, blank=True)
    dados_novos = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.organizacao} - {self.acao}"

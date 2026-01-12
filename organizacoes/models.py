import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from core.models import SoftDeleteModel, TimeStampedModel

from .utils import validate_cnpj, validate_organizacao_image


class Organizacao(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    descricao = models.TextField(blank=True)
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
    codigo_banco = models.CharField(_("Código do banco"), max_length=10, blank=True)
    nome_banco = models.CharField(_("Nome do banco"), max_length=255, blank=True)
    agencia = models.CharField(_("Agência"), max_length=10, blank=True)
    conta_corrente = models.CharField(_("Conta corrente"), max_length=20, blank=True)
    chave_pix = models.CharField(_("Chave Pix"), max_length=255, blank=True)
    mercado_pago_public_key = models.CharField(
        _("Public key do Mercado Pago"), max_length=255, blank=True
    )
    mercado_pago_access_token = models.CharField(
        _("Access token do Mercado Pago"), max_length=255, blank=True
    )
    mercado_pago_webhook_secret = models.CharField(
        _("Segredo do webhook do Mercado Pago"), max_length=255, blank=True
    )
    paypal_client_id = models.CharField(_("Client ID do PayPal"), max_length=255, blank=True)
    paypal_client_secret = models.CharField(
        _("Client secret do PayPal"), max_length=255, blank=True
    )
    paypal_webhook_secret = models.CharField(
        _("Segredo do webhook do PayPal"), max_length=255, blank=True
    )
    paypal_currency = models.CharField(
        _("Moeda padrão do PayPal"), max_length=10, blank=True, default="BRL"
    )
    nome_site = models.CharField(_("Nome do site"), max_length=12, blank=True)
    site = models.URLField(_("Site"), blank=True)
    icone_site = models.ImageField(_("Ícone do site"), upload_to="organizacoes/icones/", blank=True, null=True)
    feed_noticias = models.URLField(_("Feed de notícias"), blank=True)
    avatar = models.ImageField(upload_to="organizacoes/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="organizacoes/capas/", blank=True, null=True)
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

    def clean(self) -> None:  # type: ignore[override]
        super().clean()
        self.cnpj = validate_cnpj(self.cnpj)
        for field in ["avatar", "cover", "icone_site"]:
            file = getattr(self, field)
            if file:
                try:
                    validate_organizacao_image(file)
                except ValidationError as exc:
                    raise ValidationError({field: exc.messages}) from exc


class OrganizacaoChangeLog(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    campo_alterado = models.CharField(max_length=100)
    valor_antigo = models.TextField(blank=True, null=True)
    valor_novo = models.TextField(blank=True, null=True)
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.organizacao} - {self.campo_alterado}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self._state.adding:
            raise RuntimeError("Logs não podem ser modificados")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # type: ignore[override]
        raise RuntimeError("Logs não podem ser removidos")


class OrganizacaoFeedSync(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.CASCADE,
        related_name="feeds_sincronizados",
    )
    external_id = models.CharField(max_length=512)
    title = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("organizacao", "external_id")
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.organizacao} - {self.external_id}"


class OrganizacaoAtividadeLog(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.CASCADE,
        related_name="atividade_logs",
    )
    acao = models.CharField(max_length=50)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    detalhes = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.organizacao} - {self.acao}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self._state.adding:
            raise RuntimeError("Logs não podem ser modificados")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # type: ignore[override]
        raise RuntimeError("Logs não podem ser removidos")


class OrganizacaoRecurso(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.CASCADE,
        related_name="recursos",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    recurso = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ("organizacao", "content_type", "object_id")
        verbose_name = "Recurso de Organização"
        verbose_name_plural = "Recursos de Organização"

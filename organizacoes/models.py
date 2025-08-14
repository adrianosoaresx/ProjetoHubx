import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import SoftDeleteModel, TimeStampedModel

from .utils import validate_cnpj


class Organizacao(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    rate_limit_multiplier = models.FloatField(default=1)
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
        allowed_exts = {f".{ext.lower()}" for ext in settings.ORGANIZACOES_ALLOWED_IMAGE_EXTENSIONS}
        max_size = settings.ORGANIZACOES_MAX_IMAGE_SIZE
        for field in ["avatar", "cover"]:
            file = getattr(self, field)
            if file:
                ext = os.path.splitext(file.name)[1].lower()
                if ext not in allowed_exts:
                    raise ValidationError({field: _("Formato de imagem não suportado.")})
                if file.size > max_size:
                    raise ValidationError({field: _("Imagem excede o tamanho máximo permitido.")})


class OrganizacaoChangeLog(TimeStampedModel):
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


class OrganizacaoAtividadeLog(TimeStampedModel):
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
    detalhes = models.TextField(blank=True)

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

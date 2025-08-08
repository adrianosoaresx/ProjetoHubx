import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import SoftDeleteModel, TimeStampedModel


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
        super().delete(using=using, keep_parents=keep_parents, soft=soft)

    def soft_delete(self) -> None:
        """Marca a organização como deletada sem remover do banco."""
        self.deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted", "deleted_at"])

class OrganizacaoChangeLog(models.Model):
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
    alterado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-alterado_em"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.organizacao} - {self.campo_alterado}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self._state.adding:
            raise RuntimeError("Logs não podem ser modificados")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # type: ignore[override]
        raise RuntimeError("Logs não podem ser removidos")


class OrganizacaoAtividadeLog(models.Model):
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
    data = models.DateTimeField(auto_now_add=True)
    detalhes = models.TextField(blank=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.organizacao} - {self.acao}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self._state.adding:
            raise RuntimeError("Logs não podem ser modificados")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # type: ignore[override]
        raise RuntimeError("Logs não podem ser removidos")

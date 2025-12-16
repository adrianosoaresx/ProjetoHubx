from __future__ import annotations

# ruff: noqa: I001

import logging
import secrets
import string
import uuid
import hmac
from hashlib import sha256
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import qrcode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from accounts.models import MediaTag, UserType
from core.models import SoftDeleteManager, SoftDeleteModel, TimeStampedModel
from nucleos.models import Nucleo
from organizacoes.models import Organizacao
from pagamentos.models import Transacao
from tokens.models import TokenAcesso

from .validators import validate_uploaded_file

logger = logging.getLogger(__name__)

User = get_user_model()


class InscricaoEvento(TimeStampedModel, SoftDeleteModel):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("confirmada", "Confirmada"),
        ("cancelada", "Cancelada"),
    ]
    METODO_PAGAMENTO_CHOICES = [
        ("pix", "Pix"),
        ("boleto", "Boleto"),
        ("card", "Cartão de crédito"),
        ("faturar_avista", "Faturar à vista"),
        ("faturar_2x", "Faturar em 2x"),
        ("faturar_3x", "Faturar em 3x"),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inscricoes",
    )
    evento = models.ForeignKey(
        "Evento",
        on_delete=models.CASCADE,
        related_name="inscricoes",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pendente",
    )
    presente = models.BooleanField(default=False)
    valor_pago = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    pagamento_validado = models.BooleanField(
        default=False,
        help_text=_("Indica se o pagamento informado foi validado pela equipe."),
    )
    transacao = models.OneToOneField(
        Transacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inscricao_evento",
    )
    metodo_pagamento = models.CharField(
        max_length=20,
        choices=METODO_PAGAMENTO_CHOICES,
        null=True,
        blank=True,
    )
    comprovante_pagamento = models.FileField(
        upload_to="eventos/comprovantes/",
        null=True,
        blank=True,
    )
    data_confirmacao = models.DateTimeField(null=True, blank=True)
    qrcode_url = models.URLField(null=True, blank=True)
    check_in_realizado_em = models.DateTimeField(null=True, blank=True)
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("user", "evento")

    @property
    def motivo_cancelamento_bloqueado(self) -> str | None:
        if self.status == "cancelada":
            return _("Inscrição já cancelada.")
        if self.pagamento_validado:
            return _("Não é possível cancelar após a validação do pagamento.")
        if timezone.now() >= self.evento.data_inicio:
            return _("Não é possível cancelar após o início do evento.")
        return None

    @property
    def cancelamento_permitido(self) -> bool:
        return self.motivo_cancelamento_bloqueado is None

    def confirmar_inscricao(self) -> None:
        with transaction.atomic():
            evento = Evento.objects.select_for_update().get(pk=self.evento.pk)
            self.evento = evento
            if evento.participantes_maximo:
                confirmados = evento.inscricoes.filter(status="confirmada").count()
                if confirmados >= evento.participantes_maximo:
                    raise ValueError(_("Evento lotado."))
            qrcode_bytes: bytes | None = None
            update_fields = [
                "status",
                "data_confirmacao",
                "qrcode_url",
                "updated_at",
            ]
            self.status = "confirmada"
            self.data_confirmacao = timezone.now()
            valor_evento = evento.get_valor_para_usuario(user=self.user)
            if self.valor_pago != valor_evento:
                self.valor_pago = valor_evento
                update_fields.append("valor_pago")
            if not self.qrcode_url:
                qrcode_bytes = self.gerar_qrcode()
            self.save(update_fields=update_fields)
            EventoLog.objects.create(
                evento=self.evento,
                usuario=self.user,
                acao="inscricao_confirmada",
            )
            if qrcode_bytes:
                try:
                    from .services.email import enviar_email_confirmacao_inscricao

                    enviar_email_confirmacao_inscricao(self, qrcode_bytes)
                except Exception:
                    logger.exception("erro_email_confirmacao_inscricao", extra={"inscricao": self.pk})

    def cancelar_inscricao(self) -> None:
        if self.pagamento_validado:
            raise ValueError(_("Não é possível cancelar após a validação do pagamento."))
        if timezone.now() >= self.evento.data_inicio:
            raise ValueError("Não é possível cancelar após o início do evento.")
        was_confirmed = self.status == "confirmada"
        with transaction.atomic():
            evento = Evento.objects.select_for_update().get(pk=self.evento.pk)
            self.status = "cancelada"
            self.data_confirmacao = timezone.now()
            self.save(update_fields=["status", "data_confirmacao", "updated_at"])
            if was_confirmed and evento.numero_presentes > 0:
                evento.numero_presentes -= 1
                evento.save(update_fields=["numero_presentes", "updated_at"])
            EventoLog.objects.create(
                evento=self.evento,
                usuario=self.user,
                acao="inscricao_cancelada",
            )
            self.delete()

    def realizar_check_in(self) -> None:
        if self.check_in_realizado_em:
            return
        with transaction.atomic():
            evento = Evento.objects.select_for_update().get(pk=self.evento.pk)
            self.check_in_realizado_em = timezone.now()
            self.save(update_fields=["check_in_realizado_em", "updated_at"])
            evento.numero_presentes += 1
            evento.save(update_fields=["numero_presentes", "updated_at"])
            EventoLog.objects.create(
                evento=self.evento,
                usuario=self.user,
                acao="check_in",
            )

    def gerar_qrcode(self) -> bytes:
        """Gera um QRCode único com detalhes da inscrição e salva no armazenamento padrão."""

        inscricao_id = str(self.pk) if self.pk else None
        if not inscricao_id:
            raise ValueError("Não é possível gerar QRCode sem identificador da inscrição.")

        checksum = self.gerar_checksum(inscricao_id)
        qrcode_payload = f"inscricao:{inscricao_id}:{checksum}" if checksum else f"inscricao:{inscricao_id}"
        img = qrcode.make(qrcode_payload)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        content = buffer.getvalue()
        filename = f"inscricoes/qrcodes/{self.pk}.png"
        path = default_storage.save(filename, ContentFile(content))
        self.qrcode_url = default_storage.url(path)
        return content

    @staticmethod
    def gerar_checksum(inscricao_id: str | None) -> str | None:
        if not inscricao_id:
            return None
        secret = settings.SECRET_KEY.encode()
        return hmac.new(secret, str(inscricao_id).encode(), sha256).hexdigest()[:12]

    def get_valor_evento(self) -> Decimal | None:
        if not getattr(self, "evento", None):
            return None
        return self.evento.get_valor_para_usuario(user=getattr(self, "user", None))

    def save(self, *args, **kwargs):
        if self.pk:
            old = InscricaoEvento.all_objects.filter(pk=self.pk).first()
            if old and old.presente != self.presente:
                EventoLog.objects.create(
                    evento=self.evento,
                    usuario=self.user,
                    acao="presenca_alterada",
                    detalhes={"presente": self.presente},
                )
        super().save(*args, **kwargs)


class Evento(TimeStampedModel, SoftDeleteModel):
    class Status(models.IntegerChoices):
        ATIVO = 0, _("Ativo")
        CONCLUIDO = 1, _("Concluído")
        CANCELADO = 2, _("Cancelado")
        PLANEJAMENTO = 3, _("Planejamento")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True, null=True)
    descricao = models.TextField()
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    local = models.CharField(max_length=255)
    cidade = models.CharField(
        max_length=100,
        validators=[RegexValidator(r"^[A-Za-zÀ-ÿ\s-]+$", "Cidade inválida")],
    )
    estado = models.CharField(
        max_length=2,
        validators=[RegexValidator(r"^[A-Z]{2}$", "UF inválida")],
    )
    cep = models.CharField(
        max_length=9,
        validators=[RegexValidator(r"^\d{5}-\d{3}$", "CEP inválido")],
    )
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nucleo = models.ForeignKey(Nucleo, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.PositiveSmallIntegerField(choices=Status.choices)
    publico_alvo = models.PositiveSmallIntegerField(
        choices=[(0, "Público"), (1, "Nucleados"), (2, "Associados")]
    )
    gratuito = models.BooleanField(default=False)
    valor_associado = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Valor aplicado para associados."),
    )
    valor_nucleado = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Valor aplicado para nucleados."),
    )
    numero_presentes = models.PositiveIntegerField(default=0, editable=False)
    orcamento_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_gasto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    participantes_maximo = models.PositiveIntegerField(null=True, blank=True)
    cronograma = models.TextField(blank=True)
    informacoes_adicionais = models.TextField(blank=True)
    briefing = models.FileField(
        upload_to="eventos/briefings/",
        blank=True,
        validators=[validate_uploaded_file],
    )
    parcerias = models.FileField(
        upload_to="eventos/parcerias/",
        blank=True,
        validators=[validate_uploaded_file],
    )
    avatar = models.ImageField(
        upload_to="eventos/avatars/",
        blank=True,
        null=True,
    )
    cover = models.ImageField(
        upload_to="eventos/covers/",
        blank=True,
        null=True,
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self) -> str:
        return self.titulo

    def get_absolute_url(self) -> str:
        return reverse("eventos:evento_detalhe", args=[self.pk])

    def calcular_media_feedback(self):
        agg = self.feedbacks.aggregate(media=models.Avg("nota"))
        return agg["media"] or 0

    def endereco_completo(self) -> str:
        return f"{self.local}, {self.cidade} - {self.estado}, {self.cep}"

    def clean(self):
        super().clean()
        errors = {}
        if self.data_fim and self.data_inicio and self.data_fim <= self.data_inicio:
            errors["data_fim"] = _("A data de fim deve ser posterior à data de início.")
        if self.gratuito:
            self.valor_associado = Decimal("0.00")
            self.valor_nucleado = Decimal("0.00")
        else:
            if self.valor_associado is not None and self.valor_associado < 0:
                errors["valor_associado"] = _("Deve ser um valor positivo ou zero.")
            if self.valor_nucleado is not None and self.valor_nucleado < 0:
                errors["valor_nucleado"] = _("Deve ser um valor positivo ou zero.")

            if self.publico_alvo == 1 and self.valor_nucleado is None:
                errors["valor_nucleado"] = _("Informe o valor para nucleados.")
            if self.publico_alvo == 2 and self.valor_associado is None:
                errors["valor_associado"] = _("Informe o valor para associados.")
            if self.publico_alvo == 0 and (
                self.valor_associado is None and self.valor_nucleado is None
            ):
                errors["valor_associado"] = _("Informe ao menos um valor para o evento.")

        positive_fields = [
            "orcamento_estimado",
            "valor_gasto",
            "participantes_maximo",
        ]
        for field in positive_fields:
            value = getattr(self, field)
            if value is not None and value <= 0:
                errors[field] = _("Deve ser um valor positivo.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        base_slug = slugify(self.slug or self.titulo)
        slug_candidate = base_slug
        counter = 1
        while Evento.all_objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
            slug_candidate = f"{base_slug}-{counter}"
            counter += 1
        self.slug = slug_candidate

        if self.pk:
            old = Evento.all_objects.filter(pk=self.pk).first()
            if old:
                if old.orcamento_estimado != self.orcamento_estimado:
                    logger.info(
                        "orcamento_estimado alterado para evento %s de %s para %s",
                        self.pk,
                        old.orcamento_estimado,
                        self.orcamento_estimado,
                    )
                if old.valor_gasto != self.valor_gasto:
                    logger.info(
                        "valor_gasto alterado para evento %s de %s para %s",
                        self.pk,
                        old.valor_gasto,
                        self.valor_gasto,
                    )
        super().save(*args, **kwargs)

    def get_valor_para_usuario(self, user=None) -> Decimal | None:
        """Retorna o valor aplicável ao usuário informado."""

        if self.gratuito:
            return Decimal("0.00")

        valor_associado = self.valor_associado
        valor_nucleado = self.valor_nucleado

        if self.publico_alvo == 1:
            return valor_nucleado or valor_associado
        if self.publico_alvo == 2:
            return valor_associado or valor_nucleado

        tipo_usuario = None
        if user is not None:
            get_tipo = getattr(user, "get_tipo_usuario", None)
            if callable(get_tipo):
                tipo_usuario = get_tipo()
            else:
                tipo_usuario = get_tipo
            if isinstance(tipo_usuario, UserType):
                tipo_usuario = tipo_usuario.value
            if tipo_usuario is None:
                tipo_usuario = getattr(user, "user_type", None)

        if tipo_usuario == UserType.NUCLEADO.value and valor_nucleado is not None:
            return valor_nucleado
        if tipo_usuario == UserType.ASSOCIADO.value and valor_associado is not None:
            return valor_associado
        if getattr(user, "is_associado", False) and valor_associado is not None:
            return valor_associado
        if valor_associado is not None:
            return valor_associado
        if valor_nucleado is not None:
            return valor_nucleado
        return None


class FeedbackNota(TimeStampedModel, SoftDeleteModel):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)
    data_feedback = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Feedback de Nota"
        verbose_name_plural = "Feedbacks de Notas"
        unique_together = ("usuario", "evento")


class EventoMidia(TimeStampedModel, SoftDeleteModel):
    """Arquivos de mídia associados a um evento."""

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="midias",
    )
    file = models.FileField(upload_to="eventos/portfolio/")
    descricao = models.CharField("Descrição", max_length=255, blank=True)
    tags = models.ManyToManyField(MediaTag, related_name="evento_midias", blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Mídia do Evento"
        verbose_name_plural = "Portfólio do Evento"

    @property
    def media_type(self) -> str:
        ext = Path(self.file.name).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".gif"}:
            return "image"
        if ext in {".mp4", ".webm"}:
            return "video"
        if ext == ".pdf":
            return "pdf"
        return "other"

    def clean(self) -> None:
        super().clean()
        if self.file:
            validate_uploaded_file(self.file)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
        *,
        soft: bool = True,
    ) -> None:  # type: ignore[override]
        if not soft and self.file:
            self.file.delete(save=False)
        super().delete(using=using, keep_parents=keep_parents, soft=soft)

    def __str__(self) -> str:  # pragma: no cover - representação simples
        return f"{self.evento.titulo} - {self.file.name}"


class Convite(TimeStampedModel):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="convites")
    publico_alvo = models.CharField(max_length=100)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    local = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    cronograma = models.TextField(blank=True)
    informacoes_adicionais = models.TextField(blank=True)
    numero_participantes = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    imagem = models.ImageField(
        upload_to="eventos/convites/",
        null=True,
        blank=True,
        validators=[validate_uploaded_file],
    )
    short_code = models.CharField(max_length=16, unique=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_short_code(length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            if not Convite.objects.filter(short_code=code).exists():
                return code

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.short_code:
            self.short_code = self.generate_short_code()
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - representação simples
        return f"Convite para {self.evento} ({self.short_code})"


class PreRegistroConvite(TimeStampedModel):
    class Status(models.TextChoices):
        PENDENTE = "pendente", _("Pendente")
        ENVIADO = "enviado", _("Enviado")

    email = models.EmailField()
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="pre_registros",
    )
    codigo = models.CharField(max_length=128)
    token = models.ForeignKey(
        TokenAcesso,
        on_delete=models.CASCADE,
        related_name="pre_registros_convite",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("email", "evento")

    def marcar_enviado(self) -> None:
        self.status = self.Status.ENVIADO
        self.save(update_fields=["status", "updated_at"])


class EventoLog(TimeStampedModel, SoftDeleteModel):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="logs")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    acao = models.CharField(max_length=50)
    detalhes = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

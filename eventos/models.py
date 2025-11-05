from __future__ import annotations

# ruff: noqa: I001

import logging
import uuid
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from core.models import SoftDeleteManager, SoftDeleteModel, TimeStampedModel
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

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
        ("faturar_avista", "Faturar à vista"),
        ("faturar_2x", "Faturar em 2x"),
        ("faturar_3x", "Faturar em 3x"),
    ]

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

    def confirmar_inscricao(self) -> None:
        with transaction.atomic():
            evento = Evento.objects.select_for_update().get(pk=self.evento.pk)
            self.evento = evento
            if evento.participantes_maximo:
                confirmados = evento.inscricoes.filter(status="confirmada").count()
                if confirmados >= evento.participantes_maximo:
                    raise ValueError(_("Evento lotado."))
            update_fields = [
                "status",
                "data_confirmacao",
                "qrcode_url",
                "updated_at",
            ]
            self.status = "confirmada"
            self.data_confirmacao = timezone.now()
            valor_evento = getattr(evento, "valor", None)
            if self.valor_pago != valor_evento:
                self.valor_pago = valor_evento
                update_fields.append("valor_pago")
            if not self.qrcode_url:
                self.gerar_qrcode()
            self.save(update_fields=update_fields)
            EventoLog.objects.create(
                evento=self.evento,
                usuario=self.user,
                acao="inscricao_confirmada",
            )

    def cancelar_inscricao(self) -> None:
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

    def gerar_qrcode(self) -> None:
        """Gera um QRCode único e salva no armazenamento padrão."""
        data = f"inscricao:{self.pk}:{int(self.created_at.timestamp())}"
        img = qrcode.make(data)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        filename = f"inscricoes/qrcodes/{self.pk}.png"
        path = default_storage.save(filename, ContentFile(buffer.getvalue()))
        self.qrcode_url = default_storage.url(path)

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
    valor = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
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
            self.valor = None

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

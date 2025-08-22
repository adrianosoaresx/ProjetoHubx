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
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.models import SoftDeleteManager, SoftDeleteModel, TimeStampedModel
from nucleos.models import Nucleo
from organizacoes.models import Organizacao
from chat.models import ChatMessage

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
        ("gratuito", "Gratuito"),
        ("outro", "Outro"),
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
    observacao = models.TextField(blank=True)
    data_confirmacao = models.DateTimeField(null=True, blank=True)
    qrcode_url = models.URLField(null=True, blank=True)
    check_in_realizado_em = models.DateTimeField(null=True, blank=True)
    posicao_espera = models.PositiveIntegerField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("user", "evento")

    def confirmar_inscricao(self) -> None:
        if self.evento.participantes_maximo and self.evento.espera_habilitada:
            confirmados = self.evento.inscricoes.filter(status="confirmada").count()
            if confirmados >= self.evento.participantes_maximo:
                self.status = "pendente"
                ultimo = (
                    self.evento.inscricoes.filter(posicao_espera__isnull=False)
                    .aggregate(mx=models.Max("posicao_espera"))
                    .get("mx")
                    or 0
                )
                self.posicao_espera = ultimo + 1
                self.save(update_fields=["status", "posicao_espera", "updated_at"])
                return
        self.status = "confirmada"
        self.data_confirmacao = timezone.now()
        if not self.qrcode_url:
            self.gerar_qrcode()
        self.save(update_fields=["status", "data_confirmacao", "qrcode_url", "updated_at"])
        EventoLog.objects.create(
            evento=self.evento,
            usuario=self.user,
            acao="inscricao_confirmada",
        )

    def cancelar_inscricao(self) -> None:
        if timezone.now() >= self.evento.data_inicio:
            raise ValueError("Não é possível cancelar após o início do evento.")
        self.status = "cancelada"
        self.data_confirmacao = timezone.now()
        self.save(update_fields=["status", "data_confirmacao", "updated_at"])
        EventoLog.objects.create(
            evento=self.evento,
            usuario=self.user,
            acao="inscricao_cancelada",
        )

    def realizar_check_in(self) -> None:
        if self.check_in_realizado_em:
            return
        self.check_in_realizado_em = timezone.now()
        self.save(update_fields=["check_in_realizado_em", "updated_at"])
        EventoLog.objects.create(
            evento=self.evento,
            usuario=self.user,
            acao="check_in",
        )

    def gerar_qrcode(self) -> None:
        """Gera um QRCode único e salva no armazenamento padrão."""
        data = f"inscricao:{self.pk}:{self.created_at.timestamp()}"
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=150)
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
    coordenador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eventos_criados",
    )
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nucleo = models.ForeignKey(Nucleo, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.PositiveSmallIntegerField(choices=[(0, "Ativo"), (1, "Concluído"), (2, "Cancelado")])
    publico_alvo = models.PositiveSmallIntegerField(
        choices=[(0, "Público"), (1, "Somente nucleados"), (2, "Apenas associados")]
    )
    numero_convidados = models.PositiveIntegerField()
    numero_presentes = models.PositiveIntegerField()
    valor_ingresso = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    orcamento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    orcamento_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_gasto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    participantes_maximo = models.PositiveIntegerField(null=True, blank=True)
    espera_habilitada = models.BooleanField(default=False)
    cronograma = models.TextField(blank=True)
    informacoes_adicionais = models.TextField(blank=True)
    contato_nome = models.CharField(max_length=100)
    contato_email = models.EmailField(blank=True)
    contato_whatsapp = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to="eventos/avatars/", null=True, blank=True)
    cover = models.ImageField(upload_to="eventos/capas/", null=True, blank=True)
    briefing = models.TextField(blank=True, null=True)
    mensagem_origem = models.ForeignKey(
        "chat.ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_criados",
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

    def save(self, *args, **kwargs):
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


class ParceriaEvento(TimeStampedModel, SoftDeleteModel):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    nucleo = models.ForeignKey(Nucleo, on_delete=models.SET_NULL, null=True, blank=True)
    empresa = models.ForeignKey("empresas.Empresa", on_delete=models.PROTECT, related_name="parcerias")
    cnpj = models.CharField(
        max_length=14,
        validators=[RegexValidator(r"^\d{14}$", "CNPJ inválido")],
    )
    contato = models.CharField(max_length=150)
    representante_legal = models.CharField(max_length=150)
    tipo_parceria = models.CharField(
        max_length=20,
        choices=[
            ("patrocinio", "Patrocínio"),
            ("mentoria", "Mentoria"),
            ("mantenedor", "Mantenedor"),
            ("outro", "Outro"),
        ],
        default="patrocinio",
    )
    acordo = models.FileField(upload_to="parcerias/contratos/", blank=True, null=True)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    descricao = models.TextField(blank=True)
    avaliacao = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    comentario = models.TextField(blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-data_inicio"]
        verbose_name = "Parceria de Evento"
        verbose_name_plural = "Parcerias de Eventos"


class MaterialDivulgacaoEvento(TimeStampedModel, SoftDeleteModel):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(
        max_length=20,
        choices=[
            ("banner", "Banner"),
            ("flyer", "Flyer"),
            ("video", "Vídeo"),
            ("outro", "Outro"),
        ],
    )
    arquivo = models.FileField(upload_to="eventos/divulgacao/")
    imagem_thumb = models.ImageField(upload_to="eventos/divulgacao/thumbs/", null=True, blank=True)
    data_publicacao = models.DateField(auto_now_add=True)
    tags = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[("criado", "Criado"), ("aprovado", "Aprovado"), ("devolvido", "Devolvido")],
        default="criado",
    )
    avaliado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="materiais_avaliados",
    )
    avaliado_em = models.DateTimeField(null=True, blank=True)
    motivo_devolucao = models.TextField(blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Material de Divulgação de Evento"
        verbose_name_plural = "Materiais de Divulgação de Eventos"

    def url_publicacao(self):
        return self.arquivo.url


class BriefingEvento(TimeStampedModel, SoftDeleteModel):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    objetivos = models.TextField()
    publico_alvo = models.TextField()
    requisitos_tecnicos = models.TextField()
    cronograma_resumido = models.TextField(blank=True)
    conteudo_programatico = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    status = models.CharField(
        max_length=15,
        choices=[
            ("rascunho", "Rascunho"),
            ("orcamentado", "Orçamentado"),
            ("aprovado", "Aprovado"),
            ("recusado", "Recusado"),
        ],
        default="rascunho",
    )
    orcamento_enviado_em = models.DateTimeField(null=True, blank=True)
    aprovado_em = models.DateTimeField(null=True, blank=True)
    recusado_em = models.DateTimeField(null=True, blank=True)
    motivo_recusa = models.TextField(blank=True)
    coordenadora_aprovou = models.BooleanField(default=False)
    recusado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="briefings_recusados",
    )
    prazo_limite_resposta = models.DateTimeField(null=True, blank=True)
    avaliado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="briefings_avaliados",
    )
    avaliado_em = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Briefing de Evento"
        ordering = ["evento"]


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


class Tarefa(TimeStampedModel, SoftDeleteModel):
    """Tarefas simples relacionadas a mensagens do chat."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tarefas_criadas",
    )
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nucleo = models.ForeignKey(Nucleo, on_delete=models.SET_NULL, null=True, blank=True)
    mensagem_origem = models.ForeignKey(
        ChatMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tarefas",
    )
    status = models.CharField(
        max_length=20,
        choices=[("pendente", "Pendente"), ("concluida", "Concluída")],
        default="pendente",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("agenda:tarefa_detalhe", args=[self.pk])

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"


class TarefaLog(TimeStampedModel, SoftDeleteModel):
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name="logs")
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
        verbose_name = "Log de Tarefa"
        verbose_name_plural = "Logs de Tarefa"


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

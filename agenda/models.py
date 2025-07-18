from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

User = get_user_model()


class InscricaoEvento(TimeStampedModel):
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
    data_inscricao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pendente",
    )
    presente = models.BooleanField(default=False)
    avaliacao = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
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

    class Meta:
        unique_together = ("user", "evento")

    def confirmar_inscricao(self) -> None:
        self.status = "confirmada"
        self.data_confirmacao = timezone.now()
        self.save(update_fields=["status", "data_confirmacao", "updated_at"])

    def cancelar_inscricao(self) -> None:
        self.status = "cancelada"
        self.data_confirmacao = timezone.now()
        self.save(update_fields=["status", "data_confirmacao", "updated_at"])


class Evento(TimeStampedModel):
    titulo = models.CharField(max_length=150)
    descricao = models.TextField()
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    endereco = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=9)
    coordenador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="eventos_criados")
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
    cronograma = models.TextField(blank=True)
    informacoes_adicionais = models.TextField(blank=True)
    contato_nome = models.CharField(max_length=100)
    contato_email = models.EmailField(blank=True)
    contato_whatsapp = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to="eventos/avatars/", null=True, blank=True)
    cover = models.ImageField(upload_to="eventos/capas/", null=True, blank=True)
    briefing = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self) -> str:
        return self.titulo

    def calcular_media_feedback(self):
        agg = self.feedbacks.aggregate(media=models.Avg("nota"))
        return agg["media"] or 0


class ParceriaEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    nucleo = models.ForeignKey(Nucleo, on_delete=models.SET_NULL, null=True, blank=True)
    empresa = models.ForeignKey("empresas.Empresa", on_delete=models.PROTECT, related_name="parcerias")
    contato_adicional_nome = models.CharField(max_length=150, blank=True)
    contato_adicional_cpf = models.CharField(max_length=14, blank=True)
    whatsapp_contato = models.CharField(max_length=15)
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

    class Meta:
        verbose_name = "Parceria de Evento"
        verbose_name_plural = "Parcerias de Eventos"


class MaterialDivulgacaoEvento(models.Model):
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
    ativo = models.BooleanField(default=True)
    tags = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Material de Divulgação de Evento"
        verbose_name_plural = "Materiais de Divulgação de Eventos"

    def url_publicacao(self):
        return self.arquivo.url


class BriefingEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    objetivos = models.TextField()
    publico_alvo = models.TextField()
    requisitos_tecnicos = models.TextField()
    cronograma_resumido = models.TextField(blank=True)
    conteudo_programatico = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Briefing de Evento"
        ordering = ["evento"]


class FeedbackNota(models.Model):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)
    data_feedback = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Feedback de Nota"
        verbose_name_plural = "Feedbacks de Notas"
        unique_together = ("usuario", "evento")

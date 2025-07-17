
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel


class Evento(TimeStampedModel):
    PUBLICO_ALVO_CHOICES = [
        (0, "Público (associados e convidados)"),
        (1, "Somente nucleados"),
        (2, "Apenas associados"),
    ]

    STATUS_CHOICES = [
        (0, "Ativo"),
        (1, "Concluído"),
        (2, "Cancelado"),
    ]

    titulo = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()

    endereco = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=9)

    coordenador = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="eventos_criados"
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="eventos"
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos"
    )

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=0)
    publico_alvo = models.PositiveSmallIntegerField(choices=PUBLICO_ALVO_CHOICES, default=0)

    numero_convidados = models.PositiveIntegerField(default=0)
    numero_presentes = models.PositiveIntegerField(default=0)

    valor_ingresso = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    orcamento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    cronograma = models.TextField(blank=True)
    informacoes_adicionais = models.TextField(blank=True)

    contato_nome = models.CharField(max_length=100)
    contato_email = models.EmailField(blank=True)
    contato_whatsapp = models.CharField(max_length=15, blank=True)

    avatar = models.ImageField(upload_to="eventos/avatars/", null=True, blank=True)
    cover = models.ImageField(upload_to="eventos/capas/", null=True, blank=True)

    class Meta:
        ordering = ["data_inicio"]
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self):
        return self.titulo

    def is_concluido(self) -> bool:
        return self.status == 1 and self.data_fim < timezone.now()

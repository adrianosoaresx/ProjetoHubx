
from django.db import models
from model_utils.models import TimeStampedModel


class ParceriaEvento(TimeStampedModel):
    TIPO_PARCERIA_CHOICES = [
        ("patrocinio", "Patrocínio"),
        ("mentoria", "Mentoria"),
        ("mantenedor", "Mantenedor"),
        ("outro", "Outro"),
    ]

    evento = models.ForeignKey(
        "eventos.Evento",
        on_delete=models.CASCADE,
        related_name="parcerias"
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parcerias_evento"
    )

    empresa_razao_social = models.CharField(max_length=150)
    cnpj = models.CharField(max_length=18)
    endereco_empresa = models.TextField()

    representante_legal_nome = models.CharField(max_length=150)
    representante_legal_cpf = models.CharField(max_length=14)
    representante_legal_email = models.EmailField()

    nome_solicitante = models.CharField(max_length=150, blank=True)
    cpf_solicitante = models.CharField(max_length=14, blank=True)

    whatsapp_contato = models.CharField(max_length=15)

    tipo_parceria = models.CharField(
        max_length=20,
        choices=TIPO_PARCERIA_CHOICES,
        default="patrocinio"
    )

    class Meta:
        verbose_name = "Parceria ou Patrocínio"
        verbose_name_plural = "Parcerias e Patrocínios"

    def __str__(self):
        return f"{self.empresa_razao_social} - {self.evento.titulo}"

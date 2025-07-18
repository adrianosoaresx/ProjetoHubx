from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from core.models import TimeStampedModel
from organizacoes.models import Organizacao
from nucleos.models import Nucleo

User = get_user_model()


class Evento(TimeStampedModel):
    titulo = models.CharField(max_length=150)
    descricao = models.TextField()
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    endereco = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=9)
    coordenador = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="eventos_criados"
    )
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nucleo = models.ForeignKey(
        Nucleo, on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.PositiveSmallIntegerField(
        choices=[(0, "Ativo"), (1, "Concluído"), (2, "Cancelado")]
    )
    publico_alvo = models.PositiveSmallIntegerField(
        choices=[(0, "Público"), (1, "Somente nucleados"), (2, "Apenas associados")]
    )
    numero_convidados = models.PositiveIntegerField()
    numero_presentes = models.PositiveIntegerField()
    valor_ingresso = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    orcamento = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    cronograma = models.TextField(blank=True)
    informacoes_adicionais = models.TextField(blank=True)
    contato_nome = models.CharField(max_length=100)
    contato_email = models.EmailField(blank=True)
    contato_whatsapp = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(
        upload_to="eventos/avatars/", null=True, blank=True
    )
    cover = models.ImageField(upload_to="eventos/capas/", null=True, blank=True)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self) -> str:
        return self.titulo


class InscricaoEvento(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    presente = models.BooleanField()
    avaliacao = models.PositiveSmallIntegerField(null=True, blank=True)
    valor_pago = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    observacao = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "evento")
        verbose_name = "Inscrição de Evento"
        verbose_name_plural = "Inscrições de Eventos"


class ParceriaEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    nucleo = models.ForeignKey(
        Nucleo, on_delete=models.SET_NULL, null=True, blank=True
    )
    empresa = models.ForeignKey(
        "empresas.Empresa", on_delete=models.PROTECT, related_name="parcerias"
    )
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
    arquivo = models.FileField(upload_to="eventos/divulgacao/")
    descricao = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Material de Divulgação de Evento"
        verbose_name_plural = "Materiais de Divulgação de Eventos"


class BriefingEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    objetivos = models.TextField()
    publico_alvo = models.TextField()
    requisitos_tecnicos = models.TextField()

    class Meta:
        verbose_name = "Briefing de Evento"
        verbose_name_plural = "Briefings de Eventos"

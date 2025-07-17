
from django.db import models
from model_utils.models import TimeStampedModel


class BriefingEvento(TimeStampedModel):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("aguardando_orcamento", "Aguardando orçamento"),
        ("aguardando_aprovacao", "Aguardando aprovação"),
        ("revisar_orcamento", "Revisar orçamento"),
        ("aprovado", "Aprovado"),
        ("recusado", "Recusado"),
    ]

    evento = models.OneToOneField("eventos.Evento", on_delete=models.CASCADE, related_name="briefing")

    # Fluxo de aprovação
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="rascunho")
    coordenadora_aprovou = models.BooleanField(null=True)
    orcamento_enviado_em = models.DateTimeField(null=True, blank=True)
    prazo_limite_resposta = models.DateTimeField(null=True, blank=True)
    observacoes_resposta = models.TextField(blank=True)
    recusado_por = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    recusado_em = models.DateTimeField(null=True, blank=True)
    motivo_recusa = models.TextField(blank=True)

    # Campos do formulário
    local_reservado = models.BooleanField(default=False)
    tem_alimentacao = models.BooleanField(default=False)
    tipo_alimentacao = models.JSONField(null=True, blank=True)
    observacoes_cardapio = models.TextField(blank=True)

    tem_atracao_especial = models.BooleanField(default=False)
    tipo_atracao = models.JSONField(null=True, blank=True)
    contrapartida_palestrante = models.TextField(blank=True)
    link_profissional = models.URLField(blank=True)

    precisa_fotografia = models.BooleanField(default=False)
    tipo_profissional = models.JSONField(null=True, blank=True)
    indicacao_profissional = models.TextField(blank=True)

    detalhes_sonorizacao = models.TextField(blank=True)
    precisa_decoracao = models.BooleanField(default=False)
    detalhes_decoracao = models.TextField(blank=True)

    materiais_necessarios = models.TextField(blank=True)
    layout_mesas = models.JSONField(null=True, blank=True)

    distribuir_brindes = models.BooleanField(default=False)
    tipo_brindes = models.TextField(blank=True)

    divulgacao_conteudo = models.TextField(blank=True)
    materiais_divulgacao = models.JSONField(null=True, blank=True)
    elementos_visuais = models.TextField(blank=True)
    referencias_visuais = models.TextField(blank=True)
    realizadores_apoiadores = models.TextField(blank=True)

    data_limite_confirmacao = models.DateField(null=True, blank=True)
    patrocinadores_info = models.TextField(blank=True)
    link_formulario_patrocinadores = models.URLField(blank=True)

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from eventos.models import Evento

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from .notificacoes import enviar_distribuicao
from .saldos import aplicar_ajustes, atribuir_carteiras_padrao


def repassar_receita_ingresso(lancamento: LancamentoFinanceiro) -> None:
    """Repasse automático da receita de ingressos."""
    if (
        lancamento.tipo != LancamentoFinanceiro.Tipo.INGRESSO_EVENTO
        or lancamento.status != LancamentoFinanceiro.Status.PAGO
    ):
        return

    centro_evento = lancamento.centro_custo
    nucleo = centro_evento.nucleo

    if nucleo:
        centro_nucleo = nucleo.centros_custo.filter(tipo=CentroCusto.Tipo.NUCLEO).order_by("created_at").first()
        if not centro_nucleo:
            return
        with transaction.atomic():
            dados = {
                "centro_custo": centro_nucleo,
                "tipo": LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                "valor": lancamento.valor,
                "data_lancamento": lancamento.data_lancamento,
                "data_vencimento": lancamento.data_lancamento,
                "status": LancamentoFinanceiro.Status.PAGO,
                "descricao": "Repasse de ingresso",
            }
            atribuir_carteiras_padrao(dados)
            LancamentoFinanceiro.objects.create(**dados)
            aplicar_ajustes(
                centro_custo=centro_nucleo,
                carteira=dados.get("carteira"),
                centro_delta=lancamento.valor,
            )
    else:
        centro_org = CentroCusto.objects.filter(tipo=CentroCusto.Tipo.ORGANIZACAO).order_by("created_at").first()
        if centro_org:
            with transaction.atomic():
                dados = {
                    "centro_custo": centro_org,
                    "tipo": LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                    "valor": lancamento.valor,
                    "data_lancamento": lancamento.data_lancamento,
                    "data_vencimento": lancamento.data_lancamento,
                    "status": LancamentoFinanceiro.Status.PAGO,
                    "descricao": "Repasse de ingresso",
                }
                atribuir_carteiras_padrao(dados)
                LancamentoFinanceiro.objects.create(**dados)
                aplicar_ajustes(
                    centro_custo=centro_org,
                    carteira=dados.get("carteira"),
                    centro_delta=lancamento.valor,
                )


def distribuir_receita_evento(
    evento_id,
    valor: Decimal,
    conta_associado,
    participantes: list[tuple[ContaAssociado, Decimal]] | None = None,
) -> None:
    """Distribui receita de um evento para os centros de custo e participantes."""
    evento = Evento.objects.select_related("nucleo").get(pk=evento_id)
    if evento.status not in {0, 1}:
        raise ValidationError("Evento não permite distribuição de receita")
    valor = Decimal(valor)
    with transaction.atomic():
        if evento.nucleo:
            centro_nucleo = (
                evento.nucleo.centros_custo.filter(tipo=CentroCusto.Tipo.NUCLEO).order_by("created_at").first()
            )
            if not centro_nucleo:
                raise ValidationError("Núcleo sem centro de custo")
            dados_lanc = {
                "centro_custo": centro_nucleo,
                "conta_associado": conta_associado,
                "tipo": LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                "valor": valor,
                "data_lancamento": timezone.now(),
                "data_vencimento": timezone.now(),
                "status": LancamentoFinanceiro.Status.PAGO,
                "descricao": f"Receita evento {evento.titulo}",
            }
            atribuir_carteiras_padrao(dados_lanc)
            lanc = LancamentoFinanceiro.objects.create(**dados_lanc)
            aplicar_ajustes(
                centro_custo=centro_nucleo,
                carteira=dados_lanc.get("carteira"),
                centro_delta=valor,
            )
            if participantes:
                repasses = []
                for conta_p, perc in participantes:
                    valor_repasse = (valor * Decimal(perc)) / Decimal("100")
                    dados_repasse = {
                        "centro_custo": centro_nucleo,
                        "conta_associado": conta_p,
                        "tipo": LancamentoFinanceiro.Tipo.REPASSE,
                        "valor": valor_repasse,
                        "data_lancamento": timezone.now(),
                        "data_vencimento": timezone.now(),
                        "status": LancamentoFinanceiro.Status.PAGO,
                        "descricao": f"Repasse evento {evento.titulo}",
                    }
                    atribuir_carteiras_padrao(dados_repasse)
                    lanc_r = LancamentoFinanceiro.objects.create(**dados_repasse)
                    aplicar_ajustes(
                        centro_custo=centro_nucleo,
                        carteira=dados_repasse.get("carteira"),
                        centro_delta=-valor_repasse,
                        conta_associado=conta_p,
                        carteira_contraparte=dados_repasse.get("carteira_contraparte"),
                        contraparte_delta=valor_repasse,
                    )
                    repasses.append({"lancamento": str(lanc_r.id), "valor": str(valor_repasse)})
            for coord in evento.nucleo.coordenadores:
                enviar_distribuicao(coord, evento, valor)
        else:
            centro_evento = evento.centros_custo.filter(tipo=CentroCusto.Tipo.EVENTO).order_by("created_at").first()
            centro_org = CentroCusto.objects.filter(tipo=CentroCusto.Tipo.ORGANIZACAO).order_by("created_at").first()
            if not centro_evento or not centro_org:
                raise ValidationError("Centros de custo indisponíveis")
            metade = valor / 2
            dados_evento = {
                "centro_custo": centro_evento,
                "conta_associado": conta_associado,
                "tipo": LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                "valor": metade,
                "data_lancamento": timezone.now(),
                "data_vencimento": timezone.now(),
                "status": LancamentoFinanceiro.Status.PAGO,
                "descricao": f"Receita evento {evento.titulo}",
            }
            atribuir_carteiras_padrao(dados_evento)
            lanc_e = LancamentoFinanceiro.objects.create(**dados_evento)
            aplicar_ajustes(
                centro_custo=centro_evento,
                carteira=dados_evento.get("carteira"),
                centro_delta=metade,
            )
            dados_org = dados_evento.copy()
            dados_org["centro_custo"] = centro_org
            dados_org.pop("carteira", None)
            atribuir_carteiras_padrao(dados_org)
            lanc_o = LancamentoFinanceiro.objects.create(**dados_org)
            aplicar_ajustes(
                centro_custo=centro_org,
                carteira=dados_org.get("carteira"),
                centro_delta=metade,
            )
            if participantes:
                repasses = []
                for conta_p, perc in participantes:
                    valor_repasse = (valor * Decimal(perc)) / Decimal("100")
                    dados_repasse = {
                        "centro_custo": centro_evento,
                        "conta_associado": conta_p,
                        "tipo": LancamentoFinanceiro.Tipo.REPASSE,
                        "valor": valor_repasse,
                        "data_lancamento": timezone.now(),
                        "data_vencimento": timezone.now(),
                        "status": LancamentoFinanceiro.Status.PAGO,
                        "descricao": f"Repasse evento {evento.titulo}",
                    }
                    atribuir_carteiras_padrao(dados_repasse)
                    lanc_r = LancamentoFinanceiro.objects.create(**dados_repasse)
                    aplicar_ajustes(
                        centro_custo=centro_evento,
                        carteira=dados_repasse.get("carteira"),
                        centro_delta=-valor_repasse,
                        conta_associado=conta_p,
                        carteira_contraparte=dados_repasse.get("carteira_contraparte"),
                        contraparte_delta=valor_repasse,
                    )
                    repasses.append({"lancamento": str(lanc_r.id), "valor": str(valor_repasse)})
            enviar_distribuicao(evento.coordenador, evento, valor)

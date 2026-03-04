from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from eventos.models import Evento, InscricaoEvento
from pagamentos.models import Transacao


@dataclass
class ProcessamentoInscricaoResultado:
    inscricao: InscricaoEvento
    status: str
    message: str


def processar_inscricao_evento(
    *,
    evento: Evento,
    user,
    valor_pago: Decimal | None = None,
    metodo_pagamento: str | None = None,
    comprovante_pagamento=None,
    transacao: Transacao | None = None,
    exigir_checkout_aprovado: bool = False,
    remover_se_falhar_confirmacao: bool = False,
) -> ProcessamentoInscricaoResultado:
    inscricao, created = InscricaoEvento.all_objects.get_or_create(user=user, evento=evento)

    if inscricao.deleted:
        inscricao.deleted = False
        inscricao.deleted_at = None
        inscricao.status = "pendente"
        inscricao.presente = False

    if inscricao.status == "confirmada":
        return ProcessamentoInscricaoResultado(
            inscricao=inscricao,
            status="info",
            message=_("Você já está inscrito neste evento."),
        )

    valor_inscricao = valor_pago
    if valor_inscricao is None:
        valor_inscricao = evento.get_valor_para_usuario(user=user)
    if valor_inscricao is not None:
        inscricao.valor_pago = valor_inscricao

    if transacao:
        inscricao.transacao = transacao
        inscricao.metodo_pagamento = transacao.metodo
        inscricao.pagamento_validado = transacao.status == Transacao.Status.APROVADA
    elif metodo_pagamento:
        inscricao.metodo_pagamento = metodo_pagamento

    if comprovante_pagamento:
        inscricao.comprovante_pagamento = comprovante_pagamento

    inscricao.save()

    evento_pago = bool(
        not evento.gratuito
        and valor_inscricao is not None
        and Decimal(valor_inscricao) > Decimal("0")
    )
    transacao_aprovada = transacao is not None and transacao.status == Transacao.Status.APROVADA
    possui_comprovante = bool(inscricao.comprovante_pagamento)

    confirmar_agora = True
    if exigir_checkout_aprovado and not transacao_aprovada:
        confirmar_agora = False
    elif transacao and not transacao_aprovada:
        confirmar_agora = False
    elif evento_pago and not transacao_aprovada and not possui_comprovante:
        confirmar_agora = False

    if not confirmar_agora:
        inscricao.status = "pendente"
        inscricao.save(update_fields=["status", "updated_at"])
        return ProcessamentoInscricaoResultado(
            inscricao=inscricao,
            status="info",
            message=_("Pagamento iniciado. Confirmaremos a inscrição após a aprovação."),
        )

    try:
        inscricao.confirmar_inscricao()
    except ValueError as exc:
        if created and remover_se_falhar_confirmacao:
            inscricao.delete()
        return ProcessamentoInscricaoResultado(
            inscricao=inscricao,
            status="error",
            message=str(exc),
        )

    return ProcessamentoInscricaoResultado(
        inscricao=inscricao,
        status="success",
        message=_("Inscrição realizada."),
    )

"""Interface para o módulo de notificações do financeiro."""

from __future__ import annotations

import logging
from typing import Any

from django.utils.translation import gettext_lazy as _

from notificacoes.services.notificacoes import enviar_para_usuario

from ..models import LancamentoFinanceiro

logger = logging.getLogger(__name__)


def enviar_cobranca(user: Any, lancamento: Any) -> None:
    """Envia notificação de nova cobrança a um usuário."""

    context = {
        "nome": getattr(user, "contato", ""),
        "valor": lancamento.valor,
        "vencimento": lancamento.data_vencimento,
        "link_pagamento": "#",
    }
    try:
        tipo = getattr(lancamento, "tipo", "")
        if tipo == LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO:
            template = "mensalidade_associacao"
        elif tipo == LancamentoFinanceiro.Tipo.MENSALIDADE_NUCLEO:
            template = "mensalidade_nucleo"
        else:  # fallback genérico
            template = "financeiro_nova_cobranca"
        enviar_para_usuario(user, template, context)
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar cobrança: %s", exc)

def enviar_aviso_vencimento(user: Any, lancamento: Any) -> None:
    """Envia aviso de vencimento próximo a um usuário."""

    assunto = _("Vencimento próximo")
    corpo = _("Você possui lançamentos a vencer em breve.")
    try:
        enviar_para_usuario(
            user,
            "aviso_vencimento",
            {"assunto": str(assunto), "corpo": str(corpo)},
        )
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar aviso de vencimento: %s", exc)


def enviar_distribuicao(user: Any, evento: Any, valor: Any) -> None:
    """Notifica sobre distribuição de receita de evento."""
    context = {"nome": getattr(user, "contato", ""), "evento": evento.titulo, "valor": valor}
    try:
        enviar_para_usuario(user, "financeiro_distribuicao_receita", context)
    except Exception as exc:  # pragma: no cover
        logger.error("Falha ao enviar distribuição: %s", exc)


def enviar_ajuste(user: Any, lancamento: Any, delta: Any) -> None:
    """Notifica ajuste de lançamento."""
    context = {"nome": getattr(user, "contato", ""), "valor": delta, "lancamento": lancamento.id}
    try:
        enviar_para_usuario(user, "financeiro_ajuste_lancamento", context)
    except Exception as exc:  # pragma: no cover
        logger.error("Falha ao enviar ajuste: %s", exc)


def enviar_aporte(user: Any, lancamento: Any) -> None:
    """Notifica recebimento de aporte."""
    context = {
        "nome": getattr(user, "contato", ""),
        "valor": lancamento.valor,
        "descricao": getattr(lancamento, "descricao", ""),
    }
    try:
        enviar_para_usuario(user, "aporte_recebido", context)
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar aporte: %s", exc)


def enviar_estorno_aporte(user: Any, lancamento: Any) -> None:
    """Notifica estorno de aporte."""
    context = {
        "nome": getattr(user, "contato", ""),
        "valor": lancamento.valor,
        "descricao": getattr(lancamento, "descricao", ""),
    }
    try:
        enviar_para_usuario(user, "aporte_estornado", context)
    except Exception as exc:  # pragma: no cover - integração externa
        logger.error("Falha ao enviar estorno de aporte: %s", exc)

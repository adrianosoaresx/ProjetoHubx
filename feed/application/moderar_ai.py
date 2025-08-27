"""Caso de uso para aplicação da moderação por IA."""

from __future__ import annotations

import logging
from typing import Literal

from feed.infrastructure.moderation_ai import analisar_conteudo
from feed.models import ModeracaoPost, Post

Decision = Literal["aceito", "suspeito", "rejeitado"]

logger = logging.getLogger(__name__)


def pre_analise(texto: str, images: list[bytes] | None = None) -> Decision:
    """Executa a análise de conteúdo sem efeitos colaterais."""

    return analisar_conteudo(texto, images)


def aplicar_decisao(post: Post, decision: Decision) -> None:
    """Atualiza o status de moderação do ``post`` e registra em log."""

    status_map = {"aceito": "aprovado", "suspeito": "pendente", "rejeitado": "rejeitado"}
    mod = post.moderacao
    if mod:
        mod.status = status_map[decision]
        mod.save(update_fields=["status"])
    else:
        ModeracaoPost.objects.create(post=post, status=status_map[decision])
    logger.info("moderacao_ai", extra={"post_id": str(post.id), "decision": decision})

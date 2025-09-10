"""Ferramentas simples de moderação automática.

Este módulo simula uma análise de conteúdo baseada em IA utilizando
palavras proibidas e thresholds configuráveis. Para um ambiente real,
um modelo de linguagem deveria ser integrado aqui.
"""

from __future__ import annotations

from typing import Literal

from django.conf import settings

Decision = Literal["aceito", "suspeito", "rejeitado"]


def analisar_conteudo(texto: str, images: list[bytes] | None = None) -> Decision:
    """Analisa o ``texto`` e retorna a decisão da IA.

    A implementação atual é heurística: calcula uma pontuação proporcional
    à quantidade de palavras proibidas presentes no texto. As decisões são
    determinadas pelos limiares definidos em ``settings.FEED_AI_THRESHOLDS``.
    """

    thresholds = getattr(settings, "FEED_AI_THRESHOLDS", {"suspeito": 0.5, "rejeitado": 0.8})
    bad_words = [w.lower() for w in getattr(settings, "FEED_BAD_WORDS", [])]
    texto_lower = (texto or "").lower()
    words = texto_lower.split()
    total = len(words) or 1
    matches = sum(texto_lower.count(w) for w in bad_words)
    score = matches / total
    if score >= thresholds.get("rejeitado", 0.8):
        return "rejeitado"
    if score >= thresholds.get("suspeito", 0.5):
        return "suspeito"
    return "aceito"

from __future__ import annotations

"""Coletores de métricas simplificados para futura integração."""

class Counter:
    def __init__(self) -> None:
        self.value = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


importacao_pagamentos_total = Counter()
notificacoes_total = Counter()
cobrancas_total = Counter()

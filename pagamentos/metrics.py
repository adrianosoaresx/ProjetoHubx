from __future__ import annotations

"""Métricas Prometheus para o módulo de pagamentos."""

from prometheus_client import Counter

pagamentos_criados_total = Counter(
    "pagamentos_criados_total",
    "Pagamentos iniciados no provedor de cobrança",
    labelnames=["metodo"],
)
pagamentos_aprovados_total = Counter(
    "pagamentos_aprovados_total",
    "Pagamentos aprovados pelo provedor",
    labelnames=["metodo"],
)
pagamentos_estornados_total = Counter(
    "pagamentos_estornados_total",
    "Pagamentos estornados ou cancelados",
    labelnames=["metodo"],
)
pagamentos_erros_total = Counter(
    "pagamentos_erros_total",
    "Falhas durante o fluxo de pagamento",
    labelnames=["fase", "metodo"],
)

from __future__ import annotations

"""Prometheus metrics for tokens app."""

from prometheus_client import Counter, Histogram

# Counters
tokens_invites_created_total = Counter("tokens_invites_created_total", "Total de convites gerados")
tokens_invites_used_total = Counter("tokens_invites_used_total", "Total de convites utilizados")
tokens_invites_revoked_total = Counter("tokens_invites_revoked_total", "Total de convites revogados")
tokens_validation_fail_total = Counter("tokens_validation_fail_total", "Falhas na validação de convites")
tokens_rate_limited_total = Counter("tokens_rate_limited_total", "Requisições de tokens bloqueadas por rate limit")

# API Token counters
tokens_api_tokens_created_total = Counter(
    "tokens_api_tokens_created_total",
    "Total de tokens API gerados",
)
tokens_api_tokens_used_total = Counter(
    "tokens_api_tokens_used_total",
    "Total de tokens API utilizados",
)
tokens_api_tokens_revoked_total = Counter(
    "tokens_api_tokens_revoked_total",
    "Total de tokens API revogados",
)

# Webhook metrics
tokens_webhooks_sent_total = Counter(
    "tokens_webhooks_sent_total",
    "Total de webhooks enviados com sucesso",
)
tokens_webhooks_failed_total = Counter(
    "tokens_webhooks_failed_total",
    "Falhas no envio de webhooks",
)

# Histograms
tokens_validation_latency_seconds = Histogram("tokens_validation_latency_seconds", "Latência da validação de convites")
tokens_api_latency_seconds = Histogram("tokens_api_latency_seconds", "Latência de operações da API de tokens")
tokens_webhook_latency_seconds = Histogram(
    "tokens_webhook_latency_seconds",
    "Latência do envio de webhooks",
)

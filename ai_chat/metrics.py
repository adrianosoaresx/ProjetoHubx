from __future__ import annotations

"""Prometheus metrics for AI chat integrations."""

from prometheus_client import Counter, Histogram

chat_openai_latency_seconds = Histogram(
    "ai_chat_openai_latency_seconds",
    "Latência das chamadas ao OpenAI",
    labelnames=["phase"],
)
chat_openai_errors_total = Counter(
    "ai_chat_openai_errors_total",
    "Falhas em chamadas ao OpenAI",
    labelnames=["phase"],
)
chat_tool_latency_seconds = Histogram(
    "ai_chat_tool_latency_seconds",
    "Latência das chamadas de ferramentas internas do chat",
    labelnames=["function"],
)
chat_tool_errors_total = Counter(
    "ai_chat_tool_errors_total",
    "Falhas na execução de ferramentas internas do chat",
    labelnames=["function"],
)

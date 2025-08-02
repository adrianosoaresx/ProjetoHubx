from prometheus_client import Counter  # type: ignore

chat_mensagens_sinalizadas_total = Counter(
    "chat_mensagens_sinalizadas_total",
    "Total de mensagens sinalizadas",
    ["canal_tipo"],
)

chat_mensagens_ocultadas_total = Counter(
    "chat_mensagens_ocultadas_total",
    "Total de mensagens ocultadas",
)

chat_exportacoes_total = Counter(
    "chat_exportacoes_total",
    "Total de exportacoes de historico de chat",
    ["formato"],
)


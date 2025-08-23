from prometheus_client import Counter, Histogram  # type: ignore

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

chat_message_latency_seconds = Histogram(
    "chat_message_latency_seconds",
    "Latência em segundos das mensagens enviadas pelo WebSocket",
)

chat_notification_latency_seconds = Histogram(
    "chat_notification_latency_seconds",
    "Latência em segundos das notificações enviadas pelo WebSocket",
)


chat_resumos_total = Counter(
    "chat_resumos_total",
    "Total de resumos gerados",
    ["periodo"],
)

chat_resumo_geracao_segundos = Histogram(
    "chat_resumo_geracao_segundos",
    "Tempo de geração de resumos em segundos",
    ["periodo"],
)

# Contadores para criação de itens a partir de mensagens
chat_eventos_criados_total = Counter(
    "chat_eventos_criados_total",
    "Total de eventos criados a partir de mensagens",
)

chat_tarefas_criadas_total = Counter(
    "chat_tarefas_criadas_total",
    "Total de tarefas criadas a partir de mensagens",
)

chat_mensagens_removidas_retencao_total = Counter(
    "chat_mensagens_removidas_retencao_total",
    "Total de mensagens removidas pela política de retenção",
)

chat_retencao_canal_segundos = Histogram(
    "chat_retencao_canal_segundos",
    "Tempo de execução da política de retenção por canal em segundos",
)

chat_attachments_total = Counter(
    "chat_attachments_total",
    "Total de anexos enviados",
)

chat_categories_total = Counter(
    "chat_categories_total",
    "Total de categorias criadas",
)

# Automações Financeiras

## Objetivo

Regras configuráveis para disparar ações de cobrança e comunicação com base em gatilhos financeiros. As regras podem ser ativadas por organização, núcleo ou centro de custo e executam ações como notificações ou criação de tarefas de cobrança.

## Regras

### Escopo e Parametrização
- **Escopo**: `organizacao`, `nucleo` ou `centro`.
- **Gatilhos**:
  - `SALDO_ABAIXO` – centros com saldo menor que `limite`.
  - `LANCAMENTO_ACIMA` – lançamentos recentes com valor acima de `limite`, opcionalmente filtrados por `tipo`.
- **Ações**:
  - `ENVIAR_NOTIFICACAO`
  - `CRIAR_TAREFA_COBRANCA`
  - `SUGERIR_AJUSTE`
- **Debounce**: janela em horas para evitar repetições (`debounce_horas`, padrão 24).

### Modelos Principais
- **AutomacaoRegra**: define gatilho, ação e parâmetros em JSON.
- **AutomacaoExecucao**: log de execuções com status, motivo, afetados e `evento_hash` para idempotência.
- **TarefaCobranca**: registro simples de tarefas de cobrança.

## Execução

As regras são processadas por `processar_automacoes` (Celery Beat a cada hora).
1. Buscar regras ativas respeitando `debounce_horas`.
2. Avaliar gatilho via `RegraEngine` e calcular `evento_hash`.
3. Executar ação correspondente (`enviar_notificacao`, `criar_tarefa_cobranca` ou `sugerir_ajuste`).
4. Registrar resultado em `AutomacaoExecucao` com métricas e logs estruturados.

## API

Endpoints principais (DRF):
- `AutomacaoRegraViewSet` – CRUD de regras e ações extras:
  - `POST /automacoes/<id>/testar/` – dry‑run para prévia dos afetados.
  - `POST /automacoes/<id>/executar/` – executa imediatamente.
- `AutomacaoExecucaoViewSet` – leitura das execuções.
- `TarefaCobrancaViewSet` – CRUD básico das tarefas.

Permissões: apenas usuários com perfil **admin/financeiro** podem criar ou executar regras. Demais perfis possuem acesso apenas à leitura.

## Observabilidade

- Métricas Prometheus: `automacoes_regras_total`, `automacoes_execucoes_total{status}`, `automacoes_afetados_total{gatilho,acao}` e histograma `automacoes_duracao_ms`.
- Logs estruturados por regra e execução com `trace_id` e captura de erros via Sentry.

## Exemplos

### Regra de Saldo Baixo
```json
{
  "escopo_tipo": "centro",
  "escopo_id": "<uuid>",
  "gatilho": "SALDO_ABAIXO",
  "parametros": {"limite": 100.0},
  "acao": "CRIAR_TAREFA_COBRANCA"
}
```

## Testes

Os testes do módulo devem cobrir criação de regras, avaliação de gatilhos, execução de ações e o agendamento periódico com debounce. A cobertura mínima é de 90%.

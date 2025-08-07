# Visão Geral

O módulo **Financeiro** controla centros de custo, contas de associados e
lançamentos financeiros da plataforma. É responsável por gerar cobranças
recorrentes, registrar aportes e disponibilizar relatórios consolidados.

## Modelos

- **CentroCusto** — referência de organização de receitas e despesas. Campos:
  `nome`, `tipo`, relações opcionais com `Organizacao`, `Nucleo` ou `Evento`, e
  `saldo` acumulado.
- **ContaAssociado** — saldo financeiro vinculado a um usuário.
- **LancamentoFinanceiro** — registro genérico de entrada ou saída, com
  `tipo`, `valor`, datas de lançamento e vencimento, `status` e descrição.
- **Aporte** — proxy de `LancamentoFinanceiro` usado para registrar aportes
  internos ou externos.

## Cobranças Recorrentes

O módulo Financeiro gera automaticamente cobranças mensais de associação e de núcleos.
A tarefa `gerar_cobrancas_mensais` é executada via Celery Beat no primeiro dia de
cada mês.

Valores padrão utilizados:

- `MENSALIDADE_ASSOCIACAO`: R$50,00
- `MENSALIDADE_NUCLEO`: R$30,00
- `MENSALIDADE_VENCIMENTO_DIA`: 10

Para cada associado ativo é criado um lançamento pendente em seu respectivo centro
de custo. Caso ele participe de núcleos aprovados, é gerada também a cobrança de
mensalidade de cada núcleo correspondente. Após a criação, o sistema envia
notificações por e-mail e no aplicativo usando o app `notificacoes` com o
template `cobranca_pendente`.

## Registro de Aportes

Endpoint: `POST /api/financeiro/aportes/`

Campos obrigatórios:

- `centro_custo` — ID do centro de custo
- `valor` — valor positivo do aporte
- `descricao` — texto descritivo

Campos opcionais:

- `tipo` — `aporte_interno` (padrão) ou `aporte_externo`
- `data_lancamento` e `data_vencimento`
- `patrocinador` — para aportes externos

Somente usuários administradores podem registrar `aporte_interno`.
Após criado, o saldo do centro de custo é atualizado imediatamente.

## Endpoints

| Método e rota | Permissão | Descrição |
|---------------|-----------|-----------|
|`GET /api/financeiro/centros/`|Usuário autenticado|Lista centros de custo|
|`POST /api/financeiro/centros/`|Financeiro/Admin|Cria centro de custo|
|`POST /api/financeiro/importar-pagamentos/`|Financeiro/Admin|Pré-visualiza arquivo de importação; retorna `token_erros` quando houver rejeições|
|`POST /api/financeiro/importar-pagamentos/confirmar/`|Financeiro/Admin|Confirma importação assíncrona|
|`POST /api/financeiro/importar-pagamentos/reprocessar/<token>/`|Financeiro/Admin|Reprocessa linhas corrigidas|
|`GET /api/financeiro/importacoes/`|Financeiro/Admin|Lista importações com filtros e paginação|
|`GET /api/financeiro/importacoes/<uuid:id>/`|Financeiro/Admin|Detalha uma importação específica|
|`GET /api/financeiro/relatorios/`|Financeiro/Admin ou Coordenador|Relatório consolidado (CSV/XLSX)|
|`GET /api/financeiro/lancamentos/`|Financeiro/Admin, Coordenador ou Associado|Lista lançamentos financeiros|
|`PATCH /api/financeiro/lancamentos/<id>/`|Financeiro/Admin|Altera status para pago ou cancelado|
|`GET /api/financeiro/inadimplencias/`|Financeiro/Admin, Coordenador ou Associado|Lista pendências (CSV/XLSX)|
|`POST /api/financeiro/aportes/`|Admin (interno) ou público (externo)|Registra aporte|

A planilha de importação deve conter `centro_custo_id`, `tipo`, `valor`, `data_lancamento`, `status` e pelo menos uma das colunas `conta_associado_id` ou `email`.

## Importações de Pagamentos

`GET /api/financeiro/importacoes/`

Parâmetros opcionais: `usuario`, `arquivo`, `periodo_inicial`, `periodo_final`.

Exemplo:

```http
GET /api/financeiro/importacoes/?usuario=<id>&periodo_inicial=2024-01
```

Retorna itens paginados com `arquivo`, `total_processado`, `erros` e `status`.

```mermaid
flowchart LR
    upload[Upload] --> previa[Prévia]
    previa --> confirm[Confirmação]
    confirm --> worker[Processamento assíncrono]
    worker --> registro[ImportacaoPagamentos]
```
### Permissões
- Importação de pagamentos, geração de cobranças e relatórios completos: apenas administradores financeiros (root não possui acesso).
- Relatórios por núcleo: admin ou coordenador do núcleo.
- Inadimplências individuais: admin ou o próprio associado.


## Relatórios Financeiros

`GET /api/financeiro/relatorios/`

Parâmetros opcionais:

- `centro`: ID do centro de custo
- `nucleo`: ID do núcleo
- `periodo_inicial`: `YYYY-MM`
- `periodo_final`: `YYYY-MM`
- `tipo`: `receitas`, `despesas` ou ambos

Resposta:

```json
{
  "saldo_atual": 100.0,
  "serie": [
    {"mes": "2025-07", "receitas": 50.0, "despesas": 20.0, "saldo": 30.0}
  ],
  "inadimplencia": [
    {"mes": "2025-07", "pendentes": 50.0, "quitadas": 0.0}
  ]
}
```

## Interface Web

### Importar Pagamentos

1. Acesse **Financeiro → Importar**.
2. Escolha um arquivo `.csv` ou `.xlsx` e selecione **Pré-visualizar**. O envio é feito via HTMX e a pré-visualização aparece abaixo do formulário.
3. Erros de validação são exibidos na região de mensagens. Quando não houver problemas, o botão **Confirmar Importação** é habilitado.
4. Ao confirmar, a tarefa roda em segundo plano. Futuras integrações com o módulo de Notificações avisarão sobre erros encontrados.

### Centros de Custo

1. Em **Financeiro → Centros de Custo** use o botão **Novo Centro** para abrir o formulário no modal.
2. Preencha nome, tipo e vínculos com organização, núcleo ou evento e salve. A tabela é atualizada automaticamente.
3. Utilize as ações **Editar** ou **Excluir** de cada linha para gerenciar registros existentes.

### Relatórios

1. Acesse **Financeiro → Relatórios**.
2. Defina filtros de centro, núcleo e período e clique em **Gerar Relatório** para obter o saldo e a série temporal.
3. Use **Exportar CSV** ou **Exportar XLSX** para baixar os dados com os filtros aplicados.

> **Nota:** Todos os formulários utilizam rótulos associados, suporte a teclado e regiões `aria-live` para mensagens, atendendo às diretrizes WCAG 2.1 AA.

## Inadimplências

`GET /api/financeiro/inadimplencias/`

Parâmetros opcionais: `centro`, `nucleo`, `periodo_inicial`, `periodo_final`.

Retorna lista de lançamentos pendentes com `dias_atraso` e dados da conta do associado.

## Tarefas Celery

- `gerar_cobrancas_mensais` – executada todo início de mês para criar cobranças.
- `importar_pagamentos_async` – processa arquivos de importação em background.
- `notificar_inadimplencia` – envia lembretes para lançamentos vencidos (via `financeiro.services.notificacoes`).
  Todas registram logs no módulo e podem ter métricas Prometheus associadas. O envio utiliza o [app de notificações](notificacoes.md).

## Monitoramento

As métricas do módulo são expostas via Prometheus. Para habilitar, instale o
pacote `prometheus-client` e garanta que o servidor WSGI execute com a
variável `PROMETHEUS_PORT` definida (padrão 8001). Acesse
`http://localhost:8001/` para visualizar os contadores
`importacao_pagamentos_total`, `notificacoes_total` e `cobrancas_total`.

Novas métricas de observabilidade:

- `financeiro_importacoes_total` – importações iniciadas.
- `financeiro_importacoes_erros_total` – importações com erros.
- `financeiro_relatorios_total` – relatórios e consultas de inadimplências.
- `financeiro_tasks_total` – execuções de tarefas Celery.

## Logs de Auditoria

`GET /api/financeiro/logs/` – lista de ações registradas. Filtros: `acao`,
`usuario`, `inicio`, `fim`.

`GET /api/financeiro/task-logs/` – histórico de tarefas Celery. Filtros:
`nome_tarefa`, `status`, `inicio`, `fim`.


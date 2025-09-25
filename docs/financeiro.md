# Visão Geral

O módulo **Financeiro** centraliza o controle de lançamentos e saldos por meio
das **carteiras**. Centros de custo permanecem como classificadores de
receitas/despesas e as contas de associados são mantidas apenas para leitura
histórica. A consolidação de valores ocorre exclusivamente em `Carteira.saldo`,
utilizando lançamentos financeiros para debitar ou creditar cada carteira.

## Modelos

- **CentroCusto** — referência de organização de receitas e despesas. Campos:
  `nome`, `tipo` e relações opcionais com `Organizacao`, `Nucleo` ou `Evento`.
  O campo `saldo` passa a ser materializado apenas para relatórios legados; a
  fonte oficial de valores é a carteira operacional vinculada ao centro.
- **Carteira** — unidade de saldo. Pode pertencer a um centro ou a um associado
  (tipos `operacional`, `reserva` ou `investimento`) e mantém o campo `saldo`
  atualizado sempre que um lançamento é quitado.
- **ContaAssociado** — modelo legado utilizado apenas para associar lançamentos
  antigos. Seu campo `saldo` não deve ser consultado nem atualizado; utilize a
  carteira operacional vinculada ao associado.
- **LancamentoFinanceiro** — registro genérico de entrada ou saída, com `tipo`,
  `valor`, datas de lançamento e vencimento, `status`, `carteira` principal e
  `carteira_contraparte` quando houver contrapartida.
- **Aporte** — proxy de `LancamentoFinanceiro` usado para registrar aportes
  internos ou externos.

## Carteiras e saldos

- Cada centro de custo possui pelo menos uma carteira operacional; carteiras de
  reserva ou investimento são opcionais.
- Associados podem possuir carteiras operacionais para representar créditos e
  débitos individuais.
- A quitação de lançamentos movimenta os saldos das carteiras envolvidas. Os
  campos `saldo` de `CentroCusto` e `ContaAssociado` permanecem apenas para
  compatibilidade e não representam mais o valor real.

## Cobranças Recorrentes

O módulo Financeiro gera automaticamente cobranças mensais de associação e de
núcleos. A tarefa `gerar_cobrancas_mensais` é executada via Celery Beat no
primeiro dia de cada mês.

Valores padrão utilizados:

- `MENSALIDADE_ASSOCIACAO`: R$50,00
- `MENSALIDADE_NUCLEO`: R$30,00
- `MENSALIDADE_VENCIMENTO_DIA`: 10

Para cada associado ativo é criado um lançamento pendente no centro de custo
correspondente, vinculando a carteira operacional do centro e, quando
configurada, a carteira operacional do associado como contraparte. Caso o
associado participe de núcleos aprovados, é gerada também a cobrança de cada
núcleo correspondente. Após a criação, o sistema envia notificações por e-mail e
no aplicativo usando o app `notificacoes` com o template
`financeiro_nova_cobranca`.

## Distribuição de Receitas de Eventos

A função `distribuir_receita_evento(evento_id, valor, conta_associado)` aloca as
receitas de ingressos. Quando o evento pertence a um núcleo, todo o valor é
creditado à carteira operacional do núcleo. Sem vínculo, o valor é dividido 50/50
entre a carteira do evento e a da organização. Após a distribuição, notificações
são enviadas aos coordenadores ou organizadores responsáveis.

## Ajustes de Lançamentos

Lançamentos pagos podem ser ajustados via `POST
/api/financeiro/lancamentos/<uuid:id>/ajustar/`. O serviço cria um lançamento do
tipo `ajuste` com a diferença de valores, marca o original como ajustado e
recalcula os saldos das carteiras envolvidas. A requisição deve conter
`valor_corrigido` e `descricao_motivo` e é restrita a usuários financeiros ou
administradores.

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

Somente usuários administradores podem registrar `aporte_interno`. Após criado,
o saldo da carteira operacional do centro de custo é atualizado imediatamente.

## Endpoints

| Método e rota | Permissão | Descrição |
|---------------|-----------|-----------|
|`GET /api/financeiro/carteiras/`|Financeiro/Admin|Consulta carteiras e saldos oficiais|
|`POST /api/financeiro/carteiras/`|Financeiro/Admin|Cria ou ajusta carteiras|
|`POST /api/financeiro/importar-pagamentos/`|Financeiro/Admin|Pré-visualiza arquivo de importação; retorna `token_erros` quando houver rejeições|
|`POST /api/financeiro/importar-pagamentos/confirmar/`|Financeiro/Admin|Confirma importação assíncrona|
|`POST /api/financeiro/importar-pagamentos/reprocessar/<token>/`|Financeiro/Admin|Reprocessa linhas corrigidas|
|`GET /api/financeiro/importacoes/`|Financeiro/Admin|Lista importações com filtros e paginação|
|`GET /api/financeiro/importacoes/<uuid:id>/`|Financeiro/Admin|Detalha uma importação específica|
|`GET /api/financeiro/relatorios/`|Financeiro/Admin ou Coordenador|Relatório consolidado|
|`GET /api/financeiro/lancamentos/`|Financeiro/Admin, Coordenador ou Associado|Lista lançamentos financeiros|
|`PATCH /api/financeiro/lancamentos/<uuid:id>/`|Financeiro/Admin|Altera status para pago ou cancelado|
|`POST /api/financeiro/aportes/`|Admin (interno) ou público (externo)|Registra aporte|

A planilha de importação deve conter `centro_custo_id`, `tipo`, `valor`,
`data_lancamento`, `status` e pelo menos uma das colunas `conta_associado_id` ou
`email`. Durante o processamento, as carteiras do centro e da contraparte são
criadas automaticamente quando necessário.

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
  "saldos_por_centro": {
    "<centro_id>": 40.0
  },
  "classificacao_centros": [
    {"id": "<centro_id>", "nome": "Centro A", "tipo": "organizacao", "saldo": 40.0}
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
3. Visualize os dados com os filtros aplicados diretamente na interface.

> **Nota:** Todos os formulários utilizam rótulos associados, suporte a teclado e regiões `aria-live` para mensagens, atendendo às diretrizes WCAG 2.1 AA.

## Tarefas Celery

- `gerar_cobrancas_mensais` – executada todo início de mês para criar cobranças.
- `importar_pagamentos_async` – processa arquivos de importação em background.
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
- `financeiro_relatorios_total` – relatórios solicitados pela API auxiliar.
- `financeiro_tasks_total` – execuções de tarefas Celery.

## Logs de Auditoria

`GET /api/financeiro/logs/` – lista de ações registradas. Filtros: `acao`,
`usuario`, `inicio`, `fim`.

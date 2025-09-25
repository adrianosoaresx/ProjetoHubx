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

Os ajustes de lançamentos pagos passaram a ser executados manualmente via
administração do Django. A equipe financeira deve editar o lançamento original,
registrar a justificativa nos campos de observação e atualizar os saldos
utilizando as ferramentas internas de conciliação.

## Registro de Aportes

Os aportes são solicitados pelos associados e executados manualmente pela
equipe financeira. O formulário disponível no painel web gera apenas a
solicitação; toda a contabilização é feita por meio do Django Admin.

## Importações de Pagamentos

Com a remoção das APIs, os arquivos CSV ou XLSX devem ser encaminhados para o
time financeiro, que realiza a importação localmente. Após o processamento, os
registros continuam sendo armazenados em `ImportacaoPagamentos` para auditoria.

### Permissões
- Importação de pagamentos, geração de cobranças e relatórios completos: apenas administradores financeiros (root não possui acesso).
- Relatórios por núcleo: admin ou coordenador do núcleo.


## Relatórios Financeiros

Os relatórios consolidados são gerados sob demanda pela equipe financeira e
compartilhados em formato PDF ou planilha. A visão web continua exibindo links
informativos, porém não há mais processamento em tempo real pelo navegador.

## Interface Web

### Importar Pagamentos

1. Acesse **Financeiro → Importar** para encontrar instruções de envio.
2. Encaminhe o arquivo `.csv` ou `.xlsx` para a equipe financeira conforme orientado na página.
3. Após o processamento manual, consulte a listagem de importações para acompanhar o histórico.

### Centros de Custo

1. Em **Financeiro → Centros de Custo** use o botão **Novo Centro** para abrir o formulário no modal.
2. Preencha nome, tipo e vínculos com organização, núcleo ou evento e salve. A tabela é atualizada automaticamente.
3. Utilize as ações **Editar** ou **Excluir** de cada linha para gerenciar registros existentes.

### Relatórios

1. Acesse **Financeiro → Relatórios** para solicitar dados consolidados.
2. Utilize os canais internos para obter o relatório gerado pela equipe financeira.

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
- `financeiro_relatorios_total` – relatórios gerados manualmente.
- `financeiro_tasks_total` – execuções de tarefas Celery.

## Logs de Auditoria

As operações críticas continuam registradas em `financeiro_financeirolog`. As
consultas devem ser feitas diretamente no banco ou por relatórios internos.

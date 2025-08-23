# Financeiro

Este módulo concentra as funcionalidades financeiras do projeto.

## Modelos

### ImportacaoPagamentos
Registra cada importação de pagamentos em lote, armazenando o nome do
arquivo processado, o usuário responsável, total de linhas tratadas e
eventuais erros no formato JSON.

### FinanceiroLog
Modelo de auditoria que guarda ações relevantes (importações, geração de
cobranças, repasses e edições) com os dados anteriores e novos de cada
operação.

## Importação de pagamentos

1. Envie o arquivo para o endpoint de importação.
2. O processamento ocorre em background e pode ser acompanhado pelo
   registro em `ImportacaoPagamentos`.
3. Linhas com problemas são registradas em `errors` para posterior
   reprocessamento.
4. Os associados referenciados devem estar pré-cadastrados no sistema;
   se o e-mail informado não existir, a linha será rejeitada.

## Geração de cobranças

As cobranças mensais são geradas por uma tarefa agendada que cria os
lançamentos financeiros correspondentes e notifica os usuários.


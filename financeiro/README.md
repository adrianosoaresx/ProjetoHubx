# Financeiro

Este módulo concentra as funcionalidades financeiras do projeto.

## Modelos

### ImportacaoPagamentos
Registra cada importação de pagamentos em lote, armazenando o nome do
arquivo processado, o usuário responsável, total de linhas tratadas e
eventuais erros no formato JSON.

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

## Reconciliação de carteiras

Use o comando de management ``reconciliar_carteiras`` para comparar o saldo
materializado de cada carteira com a soma dos lançamentos quitados. Ele gera uma
tabela com o saldo atual, o valor recalculado e a diferença:

```bash
python manage.py reconciliar_carteiras
```

O comando encerra com código de saída **zero** apenas quando não há
divergências. É possível exportar o resultado para análise em planilha usando o
parâmetro opcional ``--csv``:

```bash
python manage.py reconciliar_carteiras --csv /tmp/reconciliacao.csv
```

### Checklist de rollout

- [ ] Antes de liberar uma nova versão, execute ``python manage.py
      reconciliar_carteiras`` e confirme que não há divergências ou registre o
      relatório CSV para acompanhamento.

## Views

As views deste módulo estão organizadas em dois arquivos separados:
`financeiro/views/api.py` contém as APIs utilizadas pelos clientes e
`financeiro/views/pages.py` reúne as páginas HTML. Importações devem ser
realizadas diretamente desses módulos.


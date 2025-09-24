# Migração Financeiro – Fase B (Carteiras)

## Visão Geral

A Fase B conclui a migração do módulo financeiro para o modelo baseado em
carteiras introduzido nas migrações `0011` a `0014`. Os saldos oficiais passam a
ser armazenados somente em `Carteira.saldo`, enquanto `CentroCusto` atua como
classificador e `ContaAssociado` permanece apenas por compatibilidade.

## Checklist de Migração

1. **Preparação**
   - Bloquear novas importações e cobranças automatizadas (pausar tarefas Celery
     relacionadas) e notificar equipes impactadas.
   - Fazer backup do banco de dados antes de iniciar a migração.
2. **Execução**
   - Aplicar as migrações `python manage.py migrate financeiro 0014` (ou
     `python manage.py migrate` completo).
   - Validar a criação de carteiras principais para centros e associados:
     `SELECT COUNT(*) FROM financeiro_carteira WHERE tipo = 'operacional';`.
   - Revisar lançamentos atualizados conferindo `carteira_id` e
     `carteira_contraparte_id` preenchidos.
3. **Pós-migração**
   - Rodar `python manage.py reconciliar_carteiras` para comparar o saldo
     materializado das carteiras com os lançamentos pagos.
   - Exportar divergências com `--csv` se necessário e corrigir valores antes de
     liberar o módulo.
   - Reativar as tarefas Celery e liberar novamente o fluxo de importações.
   - Comunicar a conclusão da migração e atualizar dashboards/relatórios que
     ainda consumam `CentroCusto.saldo`.

## Endpoints afetados

- `GET /api/financeiro/carteiras/` e `POST /api/financeiro/carteiras/` – novos
  para CRUD das carteiras e leitura de saldos oficiais.
- `GET /api/financeiro/lancamentos/` – respostas incluem `carteira` e
  `carteira_contraparte`. Associados continuam recebendo aviso `legacy_warning`
  quando houver referências à `ContaAssociado`.
- `PATCH /api/financeiro/lancamentos/<id>/` e endpoint de ajuste – atualização de
  status recalcula diretamente `Carteira.saldo` via serviços de pagamentos.
- `POST /api/financeiro/aportes/` – créditos são aplicados à carteira operacional
  do centro em vez de alterar `CentroCusto.saldo`.
- Relatórios e importações passam a calcular os totais a partir das carteiras
  operacionais, com criação automática de carteiras ausentes durante o processo
  de importação.

## Notas de depreciação

- `ContaAssociado` permanece somente como entidade legada; integrações não devem
  mais ler ou atualizar `saldo` diretamente. O modelo levanta exceção em ambiente
  de desenvolvimento quando salvo sem `legacy_override`.
- `CentroCusto.saldo` será removido em etapas futuras. Utilize a carteira
  operacional do centro para obter valores correntes.
- Endpoints ou relatórios que exibiam `ContaAssociado.saldo` devem ser
  atualizados para consultar `Carteira.saldo`. Qualquer divergência deve ser
  tratada com o comando `reconciliar_carteiras` até que a remoção completa dos
  campos legados seja concluída.

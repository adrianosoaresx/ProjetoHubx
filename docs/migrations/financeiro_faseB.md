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

Com a remoção das APIs do módulo financeiro, o checklist acima deve ser seguido
antes de disponibilizar novamente o acesso manual via administração do Django.
As operações listadas anteriormente (carteiras, lançamentos, aportes e
importações) passaram a ser controladas internamente pela equipe financeira.

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

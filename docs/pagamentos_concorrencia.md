# Concorrência em pagamentos

Pagamentos são confirmados tanto por polling quanto por webhooks, o que pode gerar competição por locks de linha quando múltiplos workers ou instâncias processam a mesma transação.

## Banco de dados recomendado

Para reduzir contenção e melhorar a confiabilidade das confirmações, recomendamos rodar o serviço de pagamentos em PostgreSQL em produção. O banco oferece locking mais robusto e suporte a `SELECT FOR UPDATE`, usado para proteger as atualizações de `Transacao`/`Pedido` durante confirmações e estornos.

### Feature flag

O comportamento de locking pode ser controlado via a variável de ambiente `PAGAMENTOS_ROW_LOCKS_ENABLED` (habilitada por padrão):

- Defina como `0/false/no/off` em ambientes de desenvolvimento com SQLite caso encontre `OperationalError` por falta de suporte a locks.
- Mantenha ativada em produção (especialmente com PostgreSQL) para evitar race conditions entre polling e webhooks concorrentes.

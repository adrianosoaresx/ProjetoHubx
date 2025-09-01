# AUDIT-ORGANIZACOES-001

## Escopo
Auditoria do app **Organizações** comparando o requisito REQ-ORGANIZACOES-001 com o código atual.

## Sumário de atendimento
| Requisito | Situação | Observações |
|-----------|----------|-------------|
| RF‑01 – Listar organizações | Parcial | Falta campo `inativa` para filtro |
| RF‑02 – Criar organização | Atendido | Validação de CNPJ e slug únicos |
| RF‑03 – Editar organização | Parcial | Logs apenas para campos específicos |
| RF‑04 – Excluir organização | Atendido | Soft delete restrito a root |
| RF‑05 – Inativar/Reativar | Não atendido | Usa `deleted` em vez de `inativa`/`inativada_em` |
| RF‑06 – Histórico/CSV | Atendido | Exportação implementada |
| RF‑07 – Notificar membros | Atendido | Sinal + tarefa Celery |
| RF‑08 – Associar recursos | Não atendido | Endpoints inexistentes |
| RF‑09 – Métricas/cobertura | Não atendido | Nenhuma instrumentação |
| RF‑10 – Cache/otimizações | Não atendido | Sem cache ou prefetch |
| RF‑11 – Sentry/auditoria | Não atendido | Nenhuma referência ao Sentry |

## Bugs identificados
1. `OrganizacaoToggleActiveView` não reativa entidades por filtrar `deleted=False`.
2. Task `enviar_email_membros` quebra para organizações deletadas (manager padrão).

## Recomendações
- Implementar campos de inativação (`inativa`, `inativada_em`) e expô-los nas APIs.
- Criar endpoints de associação e otimizações de desempenho.
- Integrar Sentry e métricas de observabilidade.

*Gerado em: `AUDIT-ORGANIZACOES-001.md`*

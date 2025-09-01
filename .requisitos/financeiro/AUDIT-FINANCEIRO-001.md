# AUDIT-FINANCEIRO-001

## Resumo
- Código cobre importação de pagamentos, cobranças recorrentes, centros de custo, aportes, relatórios, previsão de fluxo de caixa e integrações básicas.
- Necessárias correções de permissões e tratamento de centros, além de campos/funcionalidades ausentes (origem do lançamento, estorno de aportes, ajustes de cobranças etc.).

## Conformidade com Requisitos
| Requisito | Situação | Evidência |
|-----------|----------|-----------|
| RF-01 Importação c/ pré‑visualização e reprocesso | Atendido | `FinanceiroViewSet.importar_pagamentos`, `reprocessar_erros`​:codex-file-citation[codex-file-citation]{line_range_start=241 line_range_end=267 path=financeiro/views/__init__.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/views/__init__.py#L241-L267"}​​:codex-file-citation[codex-file-citation]{line_range_start=220 line_range_end=239 path=financeiro/views/__init__.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/views/__init__.py#L220-L239"}​ |
| RF-02 Cobranças recorrentes automáticas | Atendido (sem reajuste futuro) | `gerar_cobrancas`​:codex-file-citation[codex-file-citation]{line_range_start=49 line_range_end=109 path=financeiro/services/cobrancas.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/services/cobrancas.py#L49-L109"}​ |
| RF-03 Modelos de centro de custo, conta e lançamento | Atendido (sem origem) | `models/__init__.py`​:codex-file-citation[codex-file-citation]{line_range_start=16 line_range_end=124 path=financeiro/models/__init__.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/models/__init__.py#L16-L124"}​ |
| RF-04 Aportes e recibo | Parcial (falta estorno) | `AporteSerializer`​:codex-file-citation[codex-file-citation]{line_range_start=129 line_range_end=178 path=financeiro/serializers/__init__.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/serializers/__init__.py#L129-L178"}​ |
| RF-05 Relatórios/exportação | Parcial (sem contagem de inadimplentes) | `relatorios` service​:codex-file-citation[codex-file-citation]{line_range_start=10 line_range_end=73 path=financeiro/services/relatorios.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/services/relatorios.py#L10-L73"}​ |
| RF-06 Notificação de inadimplência | Parcial (só pós-vencimento) | `notificar_inadimplencia`​:codex-file-citation[codex-file-citation]{line_range_start=19 line_range_end=35 path=financeiro/tasks/inadimplencia.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/tasks/inadimplencia.py#L19-L35"}​ |
| RF-07 Ajustes de lançamentos | Atendido | `ajustar_lancamento`​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=32 path=financeiro/services/ajustes.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/services/ajustes.py#L1-L32"}​ |
| RF-08 Distribuição de receitas | Parcial (sem participantes) | `distribuicao.py`​:codex-file-citation[codex-file-citation]{line_range_start=59 line_range_end=116 path=financeiro/services/distribuicao.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/services/distribuicao.py#L59-L116"}​ |
| RF-09 Integrações externas | Parcial | `ERPConector` e modelos de integração​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=53 path=financeiro/services/integracoes/erp_conector.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/services/integracoes/erp_conector.py#L1-L53"}​​:codex-file-citation[codex-file-citation]{line_range_start=243 line_range_end=278 path=financeiro/models/__init__.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/models/__init__.py#L243-L278"}​ |
| RF-10 Auditoria e métricas | Atendido | `FinanceiroLog` e contadores Prometheus​:codex-file-citation[codex-file-citation]{line_range_start=197 line_range_end=233 path=financeiro/models/__init__.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/models/__init__.py#L197-L233"}​​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=33 path=financeiro/services/metrics.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/services/metrics.py#L1-L33"}​ |
| RF-11 Notificações diversas | Atendido | `services/notificacoes.py`​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=41 path=financeiro/services/notificacoes.py git_url="https://github.com/adrianosoaresx/ProjetoHubx/blob/main/financeiro/services/notificacoes.py#L1-L41"}​ |

## Bugs Identificados
- `IsFinanceiroOrAdmin` ignora papel financeiro.
- Erro de AttributeError em relatórios por uso incorreto de `_nucleos_do_usuario`.

## Planejamento de Sprints
1. **Sprint 1**: corrigir permissões e bug de relatórios; adicionar campo `origem`.
2. **Sprint 2**: estorno de aportes, notificações pré‑vencimento, contagem de inadimplentes nos relatórios.
3. **Sprint 3**: reajuste automático de cobranças futuras, distribuição de receitas a participantes, idempotência persistente na importação.

## Log
- Auditoria gerada em `2025-08-20`.

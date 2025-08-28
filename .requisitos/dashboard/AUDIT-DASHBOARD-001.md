# AUDIT-DASHBOARD-001

Data: 2025-08-13

## Cobertura de Requisitos

| ID  | Descrição                                 | Status                                              |
|-----|-------------------------------------------|-----------------------------------------------------|
| RF-01 | Filtragem Parametrizada                 | Implementado                                        |
| RF-02 | Serviço de Métricas                     | Implementado                                        |
| RF-03 | Cálculo de Variação                     | Implementado                                        |
| RF-04 | Redirecionamento por Perfil             | Implementado                                        |
| RF-05 | Métricas de Inscrições e Lançamentos    | Implementado                                        |
| RF-06 | Dashboards Personalizados               | Parcial – faltam views de edição/remoção            |
| RF-07 | Filtros Personalizados                  | Parcial – admins não removem filtros alheios; logs ausentes |
| RF-08 | Integração de Dados                     | Implementado                                        |
| RF-09 | Atualizações em Tempo Real              | Implementado (HTMX)                                 |
| RF-10 | Exportação de Métricas                  | Implementado                                        |
| RF-11 | Layout Personalizado                    | Parcial – layouts públicos invisíveis; logs ausentes |
| RF-12 | Sistema de Conquistas                   | Removido                                            |
| RF-13 | Log de Auditoria                        | Parcial – várias ações sem registro                 |
| RF-14 | Inclusão de novas métricas              | Implementado                                        |
| RNF-01 | Desempenho                             | Não verificado                                      |
| RNF-02 | Manutenibilidade                       | Não verificado (cobertura de testes desconhecida)   |
| RNF-03 | Modelo Base                            | Implementado                                        |
| RNF-05 | Escalabilidade                         | Parcial – somente HTMX                              |

## Observações
- `dashboard/signals.py` usa `cache` sem importá-lo.
- Falta CRUD completo de `DashboardConfig`.
- Layouts públicos não aparecem para usuários comuns.
- Ausência de logs em aplicar/excluir filtros/configurações e nas operações de layout.

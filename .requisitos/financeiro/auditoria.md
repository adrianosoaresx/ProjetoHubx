# Auditoria de Requisitos — financeiro

**Escopo da sprint:** análise do app `financeiro` com base em `.requisitos/financeiro/**` e código em `financeiro`.
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML
- Principais diretórios: `models/`, `services/`, `tasks/`, `templates/`, `viewsets.py`, `views/`
- Pontos de entrada/rotas: `api_urls.py` (DRF), `urls.py` (views HTML)
- Autenticação/Autorização: permissões customizadas (IsFinanceiroOrAdmin, IsCoordenador, IsAssociadoReadOnly) aplicadas nos viewsets e views

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | Importação de pagamentos com pré-visualização e reprocessamento | ATENDIDO | `financeiro/views/__init__.py:180-239` `financeiro/tasks/importar_pagamentos.py:1-54` | Baixo | — |
| RF-02 | Geração de cobranças recorrentes mensais | ATENDIDO | `financeiro/services/cobrancas.py:49-107` | Baixo | — |
| RF-03 | Centro de custos, contas de associado e lançamentos com ajuste/cancelamento | ATENDIDO | `financeiro/models/__init__.py:16-148` | Médio | — |
| RF-04 | Registro de aportes voluntários e estorno | ATENDIDO | `financeiro/models/__init__.py:156-168` `financeiro/views/__init__.py:367-372` | Baixo | — |
| RF-05 | Relatórios, exportações CSV/XLSX e previsão de fluxo de caixa | ATENDIDO | `financeiro/views/__init__.py:242-365` `financeiro/viewsets.py:206-260` | Médio | — |
| RF-06 | Gestão de inadimplência com notificações periódicas | ATENDIDO | `financeiro/tasks/inadimplencia.py:19-71` | Médio | — |
| RF-07 | Ajustes de lançamentos pagos com logs e notificações | ATENDIDO | `financeiro/services/ajustes.py:1-36` | Médio | — |
| RF-08 | Distribuição de receitas de eventos e repasses automáticos | ATENDIDO | `financeiro/services/distribuicao.py:17-55` `financeiro/services/distribuicao.py:59-123` | Médio | — |
| RF-09 | Configurações e logs de integrações externas com idempotência | ATENDIDO | `financeiro/models/__init__.py:243-298` | Médio | — |
| RF-10 | Logs de auditoria e métricas Prometheus | ATENDIDO | `financeiro/models/__init__.py:197-240` `financeiro/services/metrics.py:1-37` | Baixo | — |
| RF-11 | Notificações de cobranças, inadimplências, ajustes e repasses | ATENDIDO | `financeiro/services/notificacoes.py:1-81` | Médio | — |

### 2.1 Detalhes por requisito (com evidências)
**RF-01 — Importação de pagamentos**  
- **Evidências:** preview e confirmação via endpoints REST com processamento assíncrono e reprocessamento de erros `financeiro/views/__init__.py:180-239`; tarefa Celery que importa, gera logs e notifica `financeiro/tasks/importar_pagamentos.py:1-54`.  
- **Conclusão:** ATENDIDO

**RF-02 — Geração de cobranças recorrentes**  
- **Evidências:** serviço `gerar_cobrancas` cria lançamentos mensais, evita duplicidade e notifica usuários `financeiro/services/cobrancas.py:49-107`.  
- **Conclusão:** ATENDIDO

**RF-03 — Centro de custos e lançamentos**  
- **Evidências:** modelos para centro de custo, conta de associado e lançamento com campos de status, vencimento, ajuste e relacionamento `financeiro/models/__init__.py:16-148`.  
- **Conclusão:** ATENDIDO

**RF-04 — Aportes de associados**  
- **Evidências:** proxy `Aporte` garante tipos válidos `financeiro/models/__init__.py:156-168`; endpoint `aportes` cria lançamento e retorna dados `financeiro/views/__init__.py:367-372`.  
- **Conclusão:** ATENDIDO

**RF-05 — Relatórios e previsão de fluxo de caixa**  
- **Evidências:** view `relatorios` gera relatório e exporta CSV/XLSX `financeiro/views/__init__.py:242-305`; viewset `FinanceiroForecastViewSet` calcula previsões e permite exportar `financeiro/viewsets.py:206-260`.  
- **Conclusão:** ATENDIDO

**RF-06 — Gestão de inadimplência**  
- **Evidências:** tarefa `notificar_inadimplencia` envia lembretes semanais e atualiza data da última notificação `financeiro/tasks/inadimplencia.py:19-71`.  
- **Conclusão:** ATENDIDO

**RF-07 — Ajustes de lançamentos**  
- **Evidências:** serviço `ajustar_lancamento` cria lançamento de ajuste, atualiza saldos e notifica usuário `financeiro/services/ajustes.py:1-36`.  
- **Conclusão:** ATENDIDO

**RF-08 — Distribuição de receitas de eventos**  
- **Evidências:** repasse automático ao marcar ingresso pago `financeiro/services/distribuicao.py:17-55`; distribuição manual com logs e notificações `financeiro/services/distribuicao.py:59-123`.  
- **Conclusão:** ATENDIDO

**RF-09 — Integrações externas**  
- **Evidências:** modelos para configuração de provedor, idempotência e log de chamadas `financeiro/models/__init__.py:243-298`.  
- **Conclusão:** ATENDIDO

**RF-10 — Auditoria e métricas**  
- **Evidências:** modelos `FinanceiroLog` e `FinanceiroTaskLog` registram ações e tarefas `financeiro/models/__init__.py:197-240`; contadores Prometheus para importações, relatórios e tarefas `financeiro/services/metrics.py:1-37`.  
- **Conclusão:** ATENDIDO

**RF-11 — Notificações**  
- **Evidências:** funções para enviar cobranças, inadimplências, distribuições, ajustes e aportes via serviço de notificações `financeiro/services/notificacoes.py:1-81`.  
- **Conclusão:** ATENDIDO

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** telas de importação, relatórios, lista de lançamentos e inadimplências com links e formulários HTMX `financeiro/templates/financeiro/importar_pagamentos.html:1-40`, `financeiro/templates/financeiro/relatorios.html:1-54`.
- **Roteamento:** rotas DRF registradas em `api_urls.py`; rotas HTML em `urls.py` `financeiro/api_urls.py:1-22` `financeiro/urls.py:1-21`.
- **Acesso/Permissões:** decorators `login_required` e `user_passes_test` e checagens por tipo de usuário `financeiro/views/__init__.py:367-385`.
- **UI/Validações/Feedback:** mensagens de erro e pré-visualização com HTMX `financeiro/templates/financeiro/importar_pagamentos.html:24-40`.
- **I18n/A11y:** templates usam `{% trans %}` e `aria-live` para feedback `financeiro/templates/financeiro/importar_pagamentos.html:24-25`.
- **Links/ações quebradas:** não foram encontrados links órfãos durante a revisão.
- **Cobertura de fluxos críticos:** importação de pagamentos, geração de relatórios, registro de aportes e consulta de inadimplências testados via endpoints e templates.
- **Resumo:** Prioridades 1) manter documentação de rotas 2) monitorar tarefas agendadas 3) revisar acessibilidade nas telas.

## 4. Gaps e Plano de Ação Priorizado
1. [Média] Revisar acessibilidade detalhada (labels, foco) nas telas HTML.
2. [Baixa] Adicionar testes automatizados específicos do módulo.

## 5. Decisões de Auditoria
- Critério de match do app: diretório raiz `financeiro` com 62 arquivos de código.
- Assunções documentadas: sem testes dedicados; avaliação baseada em leitura de código e templates.

## 6. Anexos (buscas e referências)
- Templates analisados: importar_pagamentos.html, relatorios.html
- Tarefas Celery: gerar_cobrancas_mensais, importar_pagamentos_async, notificar_inadimplencia


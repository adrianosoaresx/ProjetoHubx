# Auditoria de Requisitos — dashboard

**Escopo da sprint:** análise do app `dashboard` com base em `.requisitos/dashboard/**` e código em `dashboard`.  
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML (templates/HTMX)
- Principais diretórios: `views.py`, `services.py`, `models.py`, `urls.py`, `templates/dashboard/`
- Pontos de entrada/rotas: ver `urls.py` com rotas para dashboards específicos, parciais HTMX, exportação e CRUDs de filtros, configs e layouts【F:dashboard/urls.py†L7-L34】
- Autenticação/Autorização: uso de `LoginRequiredMixin` e mixins por tipo de usuário (`SuperadminRequiredMixin`, `AdminRequiredMixin`, etc.) nas views【F:dashboard/views.py†L15-L36】【F:dashboard/views.py†L165-L189】

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | Filtragem parametrizada | ATENDIDO | `dashboard/views.py:96-140` | Baixo | — |
| RF-02 | Serviço de métricas com cache | ATENDIDO | `dashboard/services.py:452-487` | Baixo | — |
| RF-03 | Cálculo de variação percentual | ATENDIDO | `dashboard/utils.py:1-6` | Baixo | — |
| RF-04 | Redirecionamento por perfil | ATENDIDO | `dashboard/views.py:192-204` | Baixo | — |
| RF-05 | Métricas de inscrições e lançamentos | ATENDIDO | `dashboard/services.py:558-563`, `626-634` | Médio | Exibir métricas na UI |
| RF-06 | Dashboards personalizados (CRUD) | ATENDIDO | `dashboard/models.py:30-45`, `dashboard/views.py:465-503` | Baixo | — |
| RF-07 | Filtros personalizados (CRUD) | ATENDIDO | `dashboard/models.py:13-27`, `dashboard/views.py:543-567` | Baixo | — |
| RF-08 | Integração com módulos diversos | ATENDIDO | `dashboard/services.py:530-558` | Médio | — |
| RF-09 | Atualizações parciais via HTMX | ATENDIDO | `dashboard/views.py:207-330` | Baixo | — |
| RF-10 | Exportação CSV/PDF/XLSX/PNG | ATENDIDO | `dashboard/views.py:352-437` | Médio | Garantir dependências de exportação |
| RF-11 | Layout personalizado | ATENDIDO | `dashboard/models.py:81-95`, `dashboard/views.py:610-674` | Baixo | — |
| RF-12 | Sistema de conquistas | ATENDIDO | `dashboard/models.py:50-77`, `dashboard/services.py:709-729` | Baixo | — |
| RF-13 | Log de auditoria das ações | ATENDIDO | `dashboard/views.py:352-368`, `493-501`, `559-566` | Baixo | — |
| RF-14 | Inclusão de novas métricas configuráveis | NÃO ATENDIDO | — | Médio | Expor interface para cadastro de métricas |
| RNF-01 | Desempenho ≤250 ms (p95) | NÃO VERIFICÁVEL | — | Médio | medir em produção |
| RNF-02 | Manutenibilidade/Clean Architecture | NÃO VERIFICÁVEL | — | Médio | revisar cobertura de testes |
| RNF-03 | Modelos com `TimeStampedModel`/`SoftDeleteModel` | ATENDIDO | `dashboard/models.py:13-20` | Baixo | — |
| RNF-05 | Escalabilidade de tempo real | NÃO VERIFICÁVEL | — | Médio | testes de carga |

### 2.1 Detalhes por requisito (com evidências)
**RF-01 — Filtragem parametrizada**  
- Descrição: Views aceitam parâmetros de período, escopo, datas e filtros.  
- Evidências: extração de `request.GET` e repasse ao serviço【F:dashboard/views.py†L96-L140】.  
- Conclusão: ATENDIDO.

**RF-02 — Serviço de métricas com cache**  
- Descrição: `DashboardMetricsService.get_metrics()` valida parâmetros, gera chave de cache e retorna métricas.  
- Evidências: implementação com TTL de 5 minutos e controle de escopo【F:dashboard/services.py†L452-L487】.  
- Conclusão: ATENDIDO.

**RF-03 — Cálculo de variação percentual**  
- Evidências: função `get_variation` usa denominador mínimo 1【F:dashboard/utils.py†L1-L6】.  
- Conclusão: ATENDIDO.

**RF-04 — Redirecionamento por perfil**  
- Evidências: função `dashboard_redirect` direciona conforme `user_type` ou login【F:dashboard/views.py†L192-L204】.  
- Conclusão: ATENDIDO.

**RF-05 — Métricas de inscrições e lançamentos**  
- Evidências: `query_map` inclui `lancamentos_pendentes`【F:dashboard/services.py†L558-L563】 e cálculo de `inscricoes_confirmadas`【F:dashboard/services.py†L626-L634】.  
- Conclusão: ATENDIDO (necessário expor na interface).

**RF-06 — Dashboards personalizados**  
- Evidências: modelo `DashboardConfig` com validação de publicidade【F:dashboard/models.py†L30-L45】; view de criação com log e conquistas【F:dashboard/views.py†L465-L503】.  
- Conclusão: ATENDIDO.

**RF-07 — Filtros personalizados**  
- Evidências: modelo `DashboardFilter` com restrição de publicidade【F:dashboard/models.py†L13-L27】 e view de criação com `log_audit`【F:dashboard/views.py†L543-L567】.  
- Conclusão: ATENDIDO.

**RF-08 — Integração de dados**  
- Evidências: mapa de consultas utiliza modelos de Agenda, Financeiro, Feed, Chat e outros【F:dashboard/services.py†L530-L558】.  
- Conclusão: ATENDIDO.

**RF-09 — Atualizações parciais via HTMX**  
- Evidências: funções `metrics_partial`, `lancamentos_partial`, `notificacoes_partial`, `tarefas_partial` e `eventos_partial` retornam HTML parcial【F:dashboard/views.py†L207-L330】.  
- Conclusão: ATENDIDO.

**RF-10 — Exportação de métricas**  
- Evidências: `DashboardExportView` gera CSV, PDF, XLSX e PNG com registro de auditoria【F:dashboard/views.py†L352-L437】.  
- Conclusão: ATENDIDO.

**RF-11 — Layout personalizado**  
- Evidências: modelo `DashboardLayout` com validação de publicidade【F:dashboard/models.py†L81-L95】 e CRUD de layouts nas views【F:dashboard/views.py†L610-L674】.  
- Conclusão: ATENDIDO.

**RF-12 — Sistema de conquistas**  
- Evidências: modelos `Achievement`/`UserAchievement`【F:dashboard/models.py†L50-L77】 e função `check_achievements` que concede conquistas automáticas【F:dashboard/services.py†L709-L729】.  
- Conclusão: ATENDIDO.

**RF-13 — Log de auditoria**  
- Evidências: chamadas a `log_audit` em exportação, criação de configs e filtros【F:dashboard/views.py†L352-L368】【F:dashboard/views.py†L493-L501】【F:dashboard/views.py†L559-L566】.  
- Conclusão: ATENDIDO.

**RF-14 — Inclusão de novas métricas**  
- Descrição: Administradores deveriam registrar métricas sem alterar código.  
- Evidências: não há API ou interface para cadastro dinâmico.  
- Conclusão: NÃO ATENDIDO.  
- Ação: desenvolver mecanismo de configuração de métricas adicionais.

**RNF-01/02/05 — Desempenho, Manutenibilidade e Escalabilidade**  
- Evidências: requisitos dependem de medições em produção; não verificados em código.  
- Conclusão: NÃO VERIFICÁVEL.

**RNF-03 — Modelo base comum**  
- Evidências: todos os modelos herdam `TimeStampedModel` e `SoftDeleteModel`【F:dashboard/models.py†L13-L20】.  
- Conclusão: ATENDIDO.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** rotas mapeadas em `urls.py` para dashboards, parciais HTMX e CRUDs; templates como `admin.html`, `root.html`, `filter_form.html` existentes【F:dashboard/urls.py†L7-L34】【F:dashboard/templates/dashboard/config_form.html†L1-L20】.
- **Roteamento:** `dashboard_redirect` leva ao dashboard certo; endpoints de parciais expostos para HTMX【F:dashboard/views.py†L192-L207】【F:dashboard/views.py†L207-L330】.
- **Acesso/Permissões:** mixins de tipo de usuário restringem acesso a cada dashboard e CRUDs【F:dashboard/views.py†L43-L61】【F:dashboard/views.py†L610-L674】.
- **UI/Validações/Feedback:** mensagens de erro e sucesso via `django.contrib.messages` nos parciais e exportações【F:dashboard/views.py†L82-L94】【F:dashboard/views.py†L213-L232】.
- **Links/ações quebradas:** não foram identificados links quebrados; exportação depende de bibliotecas externas (WeasyPrint, openpyxl, Matplotlib).
- **Cobertura de fluxos críticos:** criação/aplicação de filtros e configurações, exportação e layouts verificados nas views acima.
- **Resumo:** Prioridades 1) corrigir falhas de testes relacionadas a campos `created` e dependência de Redis, 2) incluir métricas ausentes na UI, 3) implementar cadastro dinâmico de métricas.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Inclusão dinâmica de novas métricas (RF-14).  
2. [Média] Exibir `inscricoes_confirmadas` e `lancamentos_pendentes` no UI.  
3. [Média] Resolver erros de testes relacionados a campos inexistentes e dependência de Redis.

## 5. Decisões de Auditoria
- Critério de match do app: diretório `dashboard` na raiz continha maior quantidade de arquivos de código; nenhum outro candidato encontrado.
- Assunções: requisitos RNF dependem de ambiente de produção; não avaliados.

## 6. Anexos (buscas e referências)
- `rg` para localizar funções de parciais, exportação e conquistas.
- Contagem de templates: 23 arquivos em `dashboard/templates/dashboard/`.

# Auditoria de Requisitos — organizacoes

**Escopo da sprint:** análise do app `organizacoes` com base em `.requisitos/organizacoes/**` e código em `organizacoes/`.
**Data:** 2025-08-15
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML
- Principais diretórios: `organizacoes/`, `organizacoes/templates/organizacoes`
- Pontos de entrada/rotas: `organizacoes/urls.py`, `organizacoes/api_urls.py`
- Autenticação/Autorização: mixins `AdminRequiredMixin`, `SuperadminRequiredMixin`, permissões DRF `IsRoot` e `IsOrgAdminOrSuperuser`

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | Listar organizações com filtros | ATENDIDO | `organizacoes/api.py:27-55`, `organizacoes/templates/organizacoes/list.html:24-52` | Baixo | — |
| RF-02 | Criar organização validando CNPJ e slug | ATENDIDO | `organizacoes/serializers.py:37-61` | Baixo | — |
| RF-03 | Editar organização registrando logs | ATENDIDO | `organizacoes/serializers.py:64-109`, `organizacoes/models.py:70-99` | Baixo | — |
| RF-04 | Excluir organização (soft delete) | ATENDIDO | `organizacoes/api.py:71-78`, `organizacoes/models.py:14-38` | Médio | Garantir política de retenção |
| RF-05 | Inativar e reativar organização | ATENDIDO | `organizacoes/api.py:80-105` | Baixo | — |
| RF-06 | Consultar histórico e exportar CSV | ATENDIDO | `organizacoes/api.py:107-146` | Baixo | — |
| RF-07 | Notificar membros sobre alterações | ATENDIDO | `organizacoes/serializers.py:56-61`, `organizacoes/tasks.py:11-40` | Médio | Monitorar filas Celery |
| RF-08 | Endpoints de associação de recursos | NÃO ATENDIDO | — | Alto | Implementar endpoints `/associados/` |
| RF-09 | Métricas de desempenho e cobertura | NÃO VERIFICÁVEL | — | Médio | Instrumentar métricas p95 e coverage |
| RF-10 | Cache e otimizações de consulta | NÃO ATENDIDO | — | Médio | Aplicar Redis e `select_related/prefetch_related` |
| RF-11 | Integração com Sentry e auditoria | NÃO ATENDIDO | — | Médio | Configurar Sentry e logs centralizados |

### 2.1 Detalhes por requisito (com evidências)
**RF-01 — Listar organizações com filtros**  
- **Descrição:** API e interface devem listar organizações com busca, filtros e ordenação.  
- **Evidências:** lógica de filtros e ordenação na API; template com formulário de busca e filtros.  
- **Conclusão:** ATENDIDO.

**RF-03 — Editar organização registrando logs**  
- **Descrição:** alterações geram `OrganizacaoChangeLog` e `OrganizacaoAtividadeLog`.  
- **Evidências:** criação de logs na atualização do serializer e modelos imutáveis.  
- **Conclusão:** ATENDIDO.

**RF-07 — Notificar membros sobre alterações**  
- **Descrição:** sinal `organizacao_alterada` dispara tarefa Celery para e‑mail.  
- **Evidências:** uso do sinal no serializer e na `perform_destroy`; tarefa `enviar_email_membros`.  
- **Conclusão:** ATENDIDO.

**RF-08 — Endpoints de associação de recursos**  
- **Descrição:** requisito prevê endpoints para associar usuários, núcleos, eventos, empresas e posts.  
- **Evidências:** não há rotas ou views correspondentes.  
- **Conclusão:** NÃO ATENDIDO.  
- **Ação:** implementar endpoints dedicados ou revisar requisito.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** links para criar, editar, remover e visualizar organizações na lista. Evidência: `organizacoes/templates/organizacoes/list.html:15-106`.
- **Roteamento:** URLs e router expõem CRUD, histórico e ações de ativação. Evidências: `organizacoes/urls.py:1-20`, `organizacoes/api_urls.py:1-8`.
- **Acesso/Permissões:** mixins e permissões controlam rotas sensíveis. Evidência: `organizacoes/api.py:57-69`.
- **UI/Validações/Feedback:** mensagens de sucesso e erros via `messages` nas views. Evidência: `organizacoes/views.py:37-46`, `organizacoes/views.py:67-85`.
- **I18n/A11y:** templates usam `{% trans %}` e labels; ausência de avaliação de acessibilidade profunda.
- **Links/ações quebradas:** não foram identificados links órfãos nas telas analisadas.
- **Cobertura de fluxos críticos:** cadastro, edição, inativação e histórico cobertos.
- **Resumo:** Prioridades 1) implementar endpoints de associação; 2) adicionar métricas e cache; 3) integrar Sentry.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Implementar endpoints de associação de recursos → `organizacoes/api.py`, `tests/organizacoes/test_api.py` — 3 dias.
2. [Média] Adicionar métricas de desempenho e cache → `organizacoes/api.py`, `services.py` — 2 dias.
3. [Média] Integrar Sentry e auditoria centralizada → `organizacoes/tasks.py`, `settings` — 1 dia.

## 5. Decisões de Auditoria
- Critério de match do app: pasta `organizacoes/` foi selecionada por corresponder ao requisito com maior número de arquivos.
- Assunções documentadas: requisitos RNF-07 e RNF-08 dependem de diretrizes globais não presentes no repositório.

## 6. Anexos (buscas e referências)
- Rotas API registradas: `organizacoes/api_urls.py`.
- Templates renderizados: `organizacoes/templates/organizacoes/*.html`.

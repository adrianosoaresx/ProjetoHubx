# Auditoria de Requisitos — configuracoes

**Escopo da sprint:** análise do app `configuracoes` com base em `.requisitos/configuracoes/**` e código em `configuracoes/`.  
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML
- Principais diretórios: `configuracoes/` (models, forms, services, api, tasks, templates)
- Pontos de entrada/rotas: `Hubx/urls.py` → `/configuracoes/` (web), `/api/configuracoes/` (API)
- Autenticação/Autorização: `LoginRequiredMixin` nas views e `IsAuthenticated` nos endpoints REST

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| REQ-001 | Ativar/Desativar Notificações por E-mail | ATENDIDO | `configuracoes/models.py:45-50`, `configuracoes/forms.py:15-16` | Baixo | — |
| REQ-002 | Ativar/Desativar Notificações WhatsApp | ATENDIDO | `configuracoes/models.py:51-56`, `configuracoes/forms.py:17-18` | Baixo | — |
| REQ-003 | Ativar/Desativar Notificações Push | PARCIAL | `configuracoes/models.py:57-62`, ausência em `configuracoes/serializers.py:11-20` | Médio | Expor campos de push na API e cobrir envio nas tarefas |
| REQ-004 | Configurar Frequência por Canal | PARCIAL | `configuracoes/models.py:45-62`, `configuracoes/forms.py:31-33`, ausência de push em serializer | Médio | Incluir `frequencia_notificacoes_push` na API |
| REQ-005 | Escolher Idioma da Interface | ATENDIDO | `configuracoes/models.py:63`, `configuracoes/forms.py:21`, `configuracoes/templates/configuracoes/partials/preferencias.html:68-70` | Baixo | — |
| REQ-006 | Alternar Tema da Interface | ATENDIDO | `configuracoes/models.py:64`, `configuracoes/forms.py:22`, `configuracoes/templates/configuracoes/partials/preferencias.html:72-74` | Baixo | — |
| REQ-007 | Configurar Horários e Dia da Semana | ATENDIDO | `configuracoes/models.py:65-77`, `configuracoes/forms.py:70-95` | Baixo | — |
| REQ-008 | Configuração Automática no Cadastro | ATENDIDO | `accounts/signals.py:10-16` | Baixo | — |
| REQ-009 | Configurações Contextuais por Escopo | NÃO ATENDIDO | Apenas modelo `configuracoes/models.py:87-125`; nenhuma view/endpoint encontrado | Alto | Implementar interface/API para criar e aplicar configurações contextuais |
| REQ-010 | Registro de Alterações | ATENDIDO | `configuracoes/signals.py:39-81` | Baixo | — |
| REQ-011 | Visualizar e Editar Preferências (UI/API) | PARCIAL | `configuracoes/views.py:19-46`, `configuracoes/api.py:19-100`, falta suporte a push na API | Médio | Ampliar serializer para campos de push |
| REQ-012 | API de Preferências | PARCIAL | `configuracoes/api.py:19-100`, `configuracoes/serializers.py:11-20` | Médio | Expor todos os campos do modelo e validar push |
| REQ-013 | Teste de Notificação | ATENDIDO | `configuracoes/api.py:104-133` | Baixo | — |
| REQ-014 | Envio de Resumos Agregados | ATENDIDO | `configuracoes/tasks.py:24-60`, `configuracoes/tasks.py:78-85` | Baixo | — |
| REQ-015 | Modelos com TimeStamped/SoftDelete | PARCIAL | `configuracoes/models.py:39`, `configuracoes/models.py:87`, ausência de SoftDelete em `configuracoes/models.py:128-144` | Médio | Avaliar necessidade de SoftDelete em `ConfiguracaoContaLog` ou documentar exceção |

### 2.1 Detalhes por requisito (com evidências)
**REQ-001 — Ativar/Desativar Notificações por E-mail**  
- **Descrição:** Usuário pode habilitar/desabilitar notificações por e-mail.  
- **Evidências:** `configuracoes/models.py:45-50` define campo e frequência; formulário expõe checkbox `configuracoes/forms.py:15-16`.  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-002 — Ativar/Desativar Notificações WhatsApp**  
- **Evidências:** `configuracoes/models.py:51-56`; campo e frequência exibidos no formulário `configuracoes/forms.py:17-18`.  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-003 — Ativar/Desativar Notificações Push**  
- **Evidências:** Modelo e formulário contêm campos (`configuracoes/models.py:57-62`, `configuracoes/forms.py:19-20`), porém serializer não expõe (`configuracoes/serializers.py:11-20`).  
- **Conclusão:** PARCIAL  
- **Ação:** Incluir campos de push na API e considerar tarefas de envio.

**REQ-004 — Configurar Frequência por Canal**  
- **Evidências:** Frequências no modelo (`configuracoes/models.py:45-62`) e formulário (`configuracoes/forms.py:31-33`); serializer omite push.  
- **Conclusão:** PARCIAL  
- **Ação:** Adicionar `frequencia_notificacoes_push` no serializer.

**REQ-005 — Escolher Idioma da Interface**  
- **Evidências:** Campo `idioma` (`configuracoes/models.py:63`), exposto no formulário (`configuracoes/forms.py:21`) e template (`configuracoes/templates/configuracoes/partials/preferencias.html:68-70`).  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-006 — Alternar Tema da Interface**  
- **Evidências:** Campo `tema` (`configuracoes/models.py:64`), controle no formulário (`configuracoes/forms.py:22`) e persistência via cookie no template `configuracoes/templates/configuracoes/partials/preferencias.html:72-74`.  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-007 — Configurar Horários e Dia da Semana**  
- **Evidências:** Campos de horário e dia no modelo (`configuracoes/models.py:65-77`) e validação de obrigatoriedade no formulário (`configuracoes/forms.py:70-95`).  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-008 — Configuração Automática no Cadastro**  
- **Evidências:** Sinal cria `ConfiguracaoConta` ao salvar novo usuário (`accounts/signals.py:10-16`).  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-009 — Configurações Contextuais por Escopo**  
- **Evidências:** Apenas o modelo (`configuracoes/models.py:87-125`) e serviço de resolução (`configuracoes/services.py:55-69`); não há UI ou API para criação.  
- **Conclusão:** NÃO ATENDIDO  
- **Ação:** Implementar CRUD para `ConfiguracaoContextual` e integração na interface.

**REQ-010 — Registro de Alterações**  
- **Evidências:** Sinais capturam valores antigos e criam logs (`configuracoes/signals.py:39-81`).  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-011 — Visualização e Edição das Preferências**  
- **Evidências:** View protegida exibe formulário (`configuracoes/views.py:19-66`); API fornece endpoints (`configuracoes/api.py:19-100`), mas campos de push faltam.  
- **Conclusão:** PARCIAL  
- **Ação:** Completar API com campos de push.

**REQ-012 — API de Preferências**  
- **Evidências:** `configuracoes/api_urls.py` expõe rotas; serializer limita campos (`configuracoes/serializers.py:11-20`).  
- **Conclusão:** PARCIAL  
- **Ação:** Expandir serializer e validar entrada de push.

**REQ-013 — Teste de Notificação**  
- **Evidências:** Endpoint `TestarNotificacaoView` verifica canal habilitado e envia mensagem (`configuracoes/api.py:104-133`).  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-014 — Envio de Resumos Agregados**  
- **Evidências:** Função `_send_for_frequency` e tarefas Celery (`configuracoes/tasks.py:24-60`, `configuracoes/tasks.py:78-85`).  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-015 — Modelos TimeStamped/SoftDelete**  
- **Evidências:** `ConfiguracaoConta` e `ConfiguracaoContextual` herdam `TimeStampedModel` e `SoftDeleteModel` (`configuracoes/models.py:39`, `configuracoes/models.py:87`); `ConfiguracaoContaLog` não utiliza `SoftDeleteModel` (`configuracoes/models.py:128-144`).  
- **Conclusão:** PARCIAL  
- **Ação:** Avaliar necessidade de soft delete para logs ou justificar exceção.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** abas para Informações, Segurança, Redes e Preferências em `configuracoes/templates/configuracoes/configuracoes.html:16-23`
- **Roteamento:** rotas web e API registradas em `Hubx/urls.py:36-67`
- **Acesso/Permissões:** view `ConfiguracoesView` usa `LoginRequiredMixin` (`configuracoes/views.py:19`); API protegida por `IsAuthenticated` (`configuracoes/api.py:22`)
- **UI/Validações/Feedback:** formulários exibem mensagens de sucesso/erro (`configuracoes/views.py:82-91`); validação de horários no formulário (`configuracoes/forms.py:74-95`)
- **I18n/A11y:** templates usam `{% trans %}` e roles/aria (`configuracoes/templates/configuracoes/configuracoes.html:1-23`, `configuracoes/templates/configuracoes/partials/preferencias.html:9-44`)
- **Links/ações quebradas:** não foram identificados links quebrados; endpoints de teste retornam erro se canal desabilitado (`configuracoes/api.py:112-117`)
- **Cobertura de fluxos críticos:** edição de preferências via aba “Preferências” com persistência e atualização de cookies (`configuracoes/templates/configuracoes/partials/preferencias.html:45-116`)
- **Resumo:** Prioridades 1) expor campos de push na API, 2) implementar configurações contextuais, 3) revisar uso de SoftDelete em logs.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Implementar criação/edição de `ConfiguracaoContextual` (model já existe) – estimativa 5 pts.
2. [Média] Expor `receber_notificacoes_push` e `frequencia_notificacoes_push` no serializer e tarefas – 3 pts.
3. [Média] Avaliar SoftDelete em `ConfiguracaoContaLog` ou documentar exceção – 1 pt.

## 5. Decisões de Auditoria
- Critério de match do app: diretório `configuracoes/` (maior número de arquivos com extensões-alvo).
- Assunções documentadas: falta de UI para configurações contextuais interpretada como gap funcional.

## 6. Anexos (buscas e referências)
- `rg "ConfiguracaoContextual"` para verificar ausência de views/rotas.
- Saída de testes: falha de dependência Playwright durante `pytest tests/configuracoes -q`.

# Auditoria de Requisitos — discussao

**Escopo da sprint:** análise do app `discussao` com base em `.requisitos/discussao/**` e código em `discussao`.  
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML
- Principais diretórios: `models.py`, `views.py`, `api.py`, `serializers.py`, `tasks.py`, `templates/discussao/*`
- Pontos de entrada/rotas: `discussao/urls.py`, `discussao/api_urls.py`, `discussao/routing.py`
- Autenticação/Autorização: `LoginRequiredMixin`, `AdminRequiredMixin`, permissões DRF `IsAuthenticated`

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | CRUD de categorias com nome/descrição/slug/ícone | ATENDIDO | `discussao/views.py:36-110`, `discussao/models.py:27-64` | Baixo | — |
| RF-02 | Lista filtrável por contexto e cache 60s | ATENDIDO | `discussao/views.py:36-63` | Baixo | — |
| RF-03 | Usuário cria tópicos com título, markdown, tags e público‑alvo | ATENDIDO | `discussao/models.py:80-107`, `discussao/forms.py:27-65` | Baixo | — |
| RF-04 | Slug único, contagem de visualizações, fechado/resolvido | ATENDIDO | `discussao/models.py:86-107`, `discussao/views.py:195-216` | Baixo | — |
| RF-05 | Edição/exclusão em 15 min (autor) após isso só admin | ATENDIDO | `discussao/views.py:272-287`, `discussao/views.py:371-388` | Médio | — |
| RF-06 | Marcar tópico resolvido/melhor resposta e notificar | ATENDIDO | `discussao/views.py:426-455`, `discussao/tasks.py:35-48` | Baixo | — |
| RF-07 | Busca full‑text e ordenação por data/respostas/votos | ATENDIDO | `discussao/views.py:144-183`, `discussao/api.py:45-70` | Baixo | — |
| RF-08 | Tags reutilizáveis para filtrar tópicos | ATENDIDO | `discussao/models.py:67-75`, `discussao/forms.py:27-65` | Baixo | — |
| RF-09 | Responder tópicos com anexo e replies (`reply_to`) | ATENDIDO | `discussao/models.py:158-176`, `discussao/views.py:314-336` | Baixo | — |
| RF-10 | Edição de respostas com indicador e data de edição | ATENDIDO | `discussao/models.py:178-196`, `discussao/views.py:371-395` | Baixo | — |
| RF-11 | Votos up/down com score único por usuário | ATENDIDO | `discussao/models.py:218-237`, `discussao/views.py:404-423` | Baixo | — |
| RF-12 | Denúncia de conteúdo com log de moderação | ATENDIDO | `discussao/models.py:240-295`, `discussao/models.py:298-318` | Médio | — |
| RF-13 | Notificações assíncronas para novas respostas/resolução | ATENDIDO | `discussao/tasks.py:10-48` | Médio | — |
| RF-14 | API REST com CRUD, busca, filtros e ações | ATENDIDO | `discussao/api.py:27-148` | Médio | — |
| RF-15 | Respeito a limites/permissões na API | ATENDIDO | `discussao/api.py:72-98`, `discussao/api.py:86-95`, `discussao/api.py:150-200` | Médio | — |
| RF-16 | Integração com notificações e Agenda (futuro) | PARCIAL | `discussao/tasks.py:10-48` | Médio | Integrar com Agenda para agendar reuniões |
| RNF-01 | Suporte à pesquisa full‑text com fallback | ATENDIDO | `discussao/models.py:121-137`, `discussao/views.py:160-179` | Baixo | — |
| RNF-02 | Cache e otimizações (select_related/prefetch) | ATENDIDO | `discussao/views.py:36-63`, `discussao/views.py:144-151` | Baixo | — |
| RNF-03 | Prevenir votos/denúncias duplicados e validar anexos | PARCIAL | `discussao/models.py:218-230`, `discussao/models.py:240-269` | Médio | Adicionar validação de tipo de arquivo |
| RNF-04 | Logs de moderação e notificações | ATENDIDO | `discussao/models.py:240-295`, `discussao/tasks.py:10-48` | Baixo | — |
| RNF-05 | Tarefas Celery com retry e monitoramento | ATENDIDO | `discussao/tasks.py:10-48` | Baixo | — |
| RNF-06 | Páginas responsivas com HTMX | ATENDIDO | `discussao/templates/discussao/topicos_list.html:33-53`, `discussao/templates/discussao/topico_detail.html:20-72` | Baixo | — |

### 2.1 Detalhes por requisito
**RF-01 — CRUD de categorias**  
- **Descrição:** Administradores podem listar, criar, editar e remover categorias com campos obrigatórios.  
- **Evidências:** `discussao/views.py:36-110`, `discussao/models.py:27-64`  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**RF-05 — Edição de tópicos em até 15 minutos**  
- **Descrição:** Autor pode editar ou excluir o tópico por 15 minutos; depois apenas administradores.  
- **Evidências:** `discussao/views.py:272-287`  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**RF-12 — Denúncia e log de moderação**  
- **Descrição:** Usuários denunciam conteúdo e administradores registram ações.  
- **Evidências:** `discussao/models.py:240-295`, `discussao/models.py:298-318`  
- **Conclusão:** ATENDIDO  
- **Ação:** —

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** links para criar categorias/tópicos/responder presentes (`topicos_list.html`, `topico_detail.html`).
- **Roteamento:** URLs e rotas de API implementadas (`urls.py`, `api_urls.py`).
- **Acesso/Permissões:** `LoginRequiredMixin` e verificações de tipo de usuário nas views (`views.py`).
- **UI/Validações/Feedback:** mensagens de sucesso/erro e validações em formulários (`forms.py`, `views.py`).
- **I18n/A11y:** templates utilizam `{% trans %}` e labels básicos (`topicos_list.html`, `topico_detail.html`).
- **Links/ações quebradas:** não identificado no código estático; testes falham por dependência Redis.
- **Cobertura de fluxos críticos:** criação/edição de tópicos e respostas, votação, marcação de resolução.
- **Resumo:** Prioridades 1) tratar dependência de Redis nos testes 2) validar tipos de arquivos 3) integrar com Agenda quando definido.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Falhas em testes devido a dependência do Redis → adicionar mock ou fallback de cache/mensageria.
2. [Média] Ausência de validação de tipos de arquivos anexados → implementar validação em `RespostaDiscussao`/forms.
3. [Baixa] Integração com Agenda não implementada → definir estratégia e endpoints.

## 5. Decisões de Auditoria
- Critério de match do app: diretório `discussao/` na raiz possui maior número de arquivos de código.
- Assunções documentadas: integração com Agenda considerada futura conforme requisitos.

## 6. Anexos (buscas e referências)
- Rotas API registradas em `discussao/api_urls.py`
- Templates listados em `discussao/templates/discussao/`

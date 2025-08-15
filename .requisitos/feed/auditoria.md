# Auditoria de Requisitos — feed

**Escopo da sprint:** análise do app `feed` com base em `.requisitos/feed/**` e código em `feed`.
**Data:** 2025-08-15
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML (Django templates)
- Principais diretórios: `feed/`, `feed/templates/feed/`
- Pontos de entrada/rotas: `feed/urls.py`, `feed/api_urls.py`
- Autenticação/Autorização: `LoginRequiredMixin`, `@login_required`, `@permission_required`, `IsAuthenticated`, rate limiting

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| REQ-001 | Listar posts com filtros e busca textual | ATENDIDO | `feed/api.py:184-245`, `feed/views.py:120-144` | Baixo | — |
| REQ-002 | Criar post com texto ou mídia validada | ATENDIDO | `feed/api.py:63-94`, `feed/views.py:157-198` | Baixo | — |
| REQ-003 | Editar e remover posts (soft delete) | ATENDIDO | `feed/views.py:245-308`, `feed/models.py:48-69` | Baixo | — |
| REQ-004 | Upload para storage com validação e suporte a vídeo | ATENDIDO | `feed/services.py:12-35`, `feed/models.py:61-63` | Médio | Monitorar limites de tamanho |
| REQ-005 | Tags e filtragem por tags | ATENDIDO | `feed/models.py:16-23,66`, `feed/api.py:206-212` | Baixo | — |
| REQ-006 | Moderação automática por palavras proibidas | ATENDIDO | `feed/models.py:83-94`, `feed/application/moderar_ai.py:15-23` | Médio | Ajustar lista de palavras |
| REQ-007 | Denunciar posts com limiar para pendente | ATENDIDO | `feed/api.py:304-312`, `feed/application/denunciar_post.py:12-24` | Médio | — |
| REQ-008 | Moderação manual de posts | ATENDIDO | `feed/api.py:314-332`, `feed/views.py:313-331` | Baixo | — |
| REQ-009 | Curtidas com toggle | ATENDIDO | `feed/models.py:97-108`, `feed/views.py:244-253` | Baixo | — |
| REQ-010 | Bookmarks de posts | ATENDIDO | `feed/models.py:125-136`, `feed/api.py:295-302` | Baixo | — |
| REQ-011 | Comentários e respostas | ATENDIDO | `feed/models.py:139-152`, `feed/views.py:221-241` | Baixo | — |
| REQ-012 | Reações (like/share) | PARCIAL | `feed/models.py:178-196` | Médio | Expor endpoints e UI para reações |
| REQ-013 | Registro de visualizações | PARCIAL | `feed/models.py:199-211` | Médio | Integrar criação de `PostView` nas views |
| REQ-014 | Notificações de novos posts e interações | ATENDIDO | `feed/tasks.py:15-44`, `feed/tasks.py:46-66` | Baixo | — |
| REQ-015 | Rate limiting e cache nas listagens | ATENDIDO | `feed/api.py:166-182,247-282`, `feed/views.py:151-154` | Baixo | — |
| REQ-016 | Métricas Prometheus | ATENDIDO | `feed/tasks.py:1-13`, `feed/api.py:284-290` | Baixo | — |
| REQ-017 | Configurar plugins de feed por organização | ATENDIDO | `feed/models.py:29-45` | Baixo | — |
| REQ-018 | API REST para posts, comentários, likes etc. | ATENDIDO | `feed/api_urls.py:1-17` | Baixo | — |

### 2.1 Detalhes por requisito (com evidências)
**REQ-001 — Listar posts com filtros e busca textual**
- **Descrição:** Listagem paginada por tipo de feed, organização, núcleo, evento, tags e busca OR.
- **Evidências:**
  - `feed/api.py:184-245`
  - `feed/views.py:120-144`
- **Conclusão:** ATENDIDO
- **Ação:** —

**REQ-012 — Reações (like/share)**
- **Descrição:** Registrar reações adicionais além de curtidas.
- **Evidências:**
  - `feed/models.py:178-196`
- **Conclusão:** PARCIAL — modelo existe, mas não há views/API públicas.
- **Ação:** Implementar endpoints e UI para registrar/visualizar reações.

**REQ-013 — Registro de visualizações**
- **Descrição:** Armazenar abertura/fechamento de posts para métricas.
- **Evidências:**
  - `feed/models.py:199-211`
- **Conclusão:** PARCIAL — apenas modelo, sem uso nas views.
- **Ação:** Criar hooks nas views/API para salvar `PostView` ao abrir/fechar posts.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** Rotas mapeadas em `feed/urls.py` levam a listagem, mural pessoal e CRUD de posts; templates como `feed/feed.html` e `feed/nova_postagem.html` exibem botões de ação.
- **Roteamento:** URLs declaradas em `feed/urls.py` e API em `feed/api_urls.py` cobrem listagem, criação, edição, moderação e interações.
- **Acesso/Permissões:** Uso de `LoginRequiredMixin`, `@login_required`, `@permission_required` e `IsAuthenticated` restringe operações.
- **UI/Validações/Feedback:** Formulários apresentam mensagens de erro via validações em serializers e forms; templates utilizam HTMX para atualizações parciais.
- **I18n/A11y:** Templates utilizam rótulos e estrutura simples; sem evidências de internacionalização avançada.
- **Links/ações quebradas:** nenhum link óbvio quebrado identificado nas rotas principais.
- **Cobertura de fluxos críticos:** criação, edição, exclusão, curtidas e comentários cobertos; fluxo de reações e visualizações carece de implementação.
- **Resumo:** Prioridades 1) implementar reações completas, 2) registrar visualizações, 3) garantir testes de upload e renderização de templates.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Reações sem endpoints/templating → adicionar API e botões correspondentes.
2. [Média] Registro de visualizações não integrado → hooks em `PostDetailView` e API para salvar `PostView`.
3. [Média] Melhorar testes e tratamento de uploads para evitar falhas de `ContentNotRenderedError` e erros de `upload_media`.

## 5. Decisões de Auditoria
- Critério de match do app: diretório `feed` foi o único correspondente ao nome do app no repositório.
- Assunções documentadas: não foram localizados endpoints para reações nem uso de `PostView`; considerou-se ausência como implementação parcial.

## 6. Anexos (buscas e referências)
- `rg "def toggle_like" -n feed/`
- `rg "is_ratelimited" -n feed/`


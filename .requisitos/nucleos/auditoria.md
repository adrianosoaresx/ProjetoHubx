# Auditoria de Requisitos — nucleos

**Escopo da sprint:** análise do app `nucleos` com base em `.requisitos/nucleos/**` e código em `nucleos/`.
**Data:** 2025-08-15
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML
- Principais diretórios: `nucleos/` (models, api, views, templates)
- Pontos de entrada/rotas: API `nucleos/api_urls.py`, views web `nucleos/urls.py`
- Autenticação/Autorização: permissões `IsAuthenticated`, `IsAdmin`, `IsAdminOrCoordenador`, mixins `LoginRequiredMixin`, `AdminRequiredMixin`

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|---------------|--------------------|
| RF-01 | Criar núcleo | ATENDIDO | `nucleos/api.py:118-127` | Baixo | — |
| RF-02 | Listar núcleos com paginação e cache | ATENDIDO | `nucleos/api.py:128-146` | Baixo | — |
| RF-03 | Editar núcleo | ATENDIDO | `nucleos/views.py:88-105` | Baixo | — |
| RF-04 | Deletar núcleo com soft delete | ATENDIDO | `nucleos/api.py:150-151` | Baixo | — |
| RF-05 | Solicitar participação | ATENDIDO | `nucleos/api.py:224-254` | Baixo | — |
| RF-06 | Decidir participação (aprovar/recusar) | ATENDIDO | `nucleos/api.py:256-308` | Baixo | — |
| RF-07 | Suspender/reativar membro | ATENDIDO | `nucleos/api.py:310-364` | Médio | Monitorar ajustes de cobrança |
| RF-08 | Gerenciar convites | ATENDIDO | `nucleos/api.py:153-200` | Baixo | — |
| RF-09 | Aceitar convite via token | ATENDIDO | `nucleos/api.py:86-115` | Baixo | — |
| RF-10 | Designar coordenador suplente | ATENDIDO | `nucleos/api.py:420-459` | Baixo | — |
| RF-11 | Exportar lista de membros | ATENDIDO | `nucleos/api.py:512-569` | Baixo | — |
| RF-12 | Publicar posts no feed | ATENDIDO | `nucleos/api.py:202-222` | Baixo | — |
| RF-13 | Consultar status do membro | ATENDIDO | `nucleos/api.py:366-380` | Baixo | — |
| RF-14 | Consultar métricas do núcleo | ATENDIDO | `nucleos/api.py:571-589` | Baixo | — |
| RF-15 | Relatório geral de núcleos | ATENDIDO | `nucleos/api.py:592-639` | Baixo | — |
| RF-16 | Gerir coordenadores (atribuir/remover) | PARCIAL | `nucleos/views.py:217-224` | Médio | Expor endpoints API para alterar papel |
| RF-17 | Listar núcleos do usuário autenticado | NÃO ATENDIDO | — | Médio | Implementar endpoint dedicado |

### 2.1 Detalhes por requisito
**RF-02 — Listar núcleos com cache**  
- **Descrição:** GET `/api/nucleos/?organizacao=<id>` retorna `X-Cache` HIT/MISS.  
- **Evidências:**  
  - `nucleos/api.py:128-146`  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**RF-08 — Gerenciar convites**  
- **Descrição:** emissão e revogação de convites respeitando cota diária.  
- **Evidências:**  
  - `nucleos/api.py:153-175` (emissão)
  - `nucleos/api.py:177-200` (revogação)  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**RF-16 — Gerir coordenadores**  
- **Descrição:** atribuição de papel coordenador.  
- **Evidências:**  
  - `nucleos/views.py:217-224`  
- **Conclusão:** PARCIAL (apenas via view HTML, sem endpoint API).  
- **Ação:** criar endpoints REST para promover/rebaixar membros.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** links para listar, criar e detalhar núcleos em `nucleos/urls.py` e `templates/nucleos/list.html` (`lines 13-30`).
- **Roteamento:** API registrada em `nucleos/api_urls.py` e páginas web em `nucleos/urls.py:7-64`.
- **Acesso/Permissões:** uso de `IsAuthenticated`, `IsAdmin`, `IsAdminOrCoordenador` e mixins de login e cargo.
- **UI/Validações/Feedback:** formulários com mensagens de sucesso/erro em `views.py` (`76-85`, `103-105`, `108-115`).
- **I18n/A11y:** templates com `{% trans %}` e atributos `aria-label` (`templates/nucleos/list.html:10-33`).
- **Links/ações quebradas:** não identificado.
- **Cobertura de fluxos críticos:** criação, solicitação e aprovação de membros validados nos templates e actions API.
- **Resumo:** Prioridades 1) endpoints para gerir coordenadores, 2) endpoint para listar núcleos do usuário, 3) monitorar suspensões/cobranças.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Implementar endpoint para listar núcleos do usuário (`RF-17`).
2. [Média] Expor API para alterar papel de membros (`RF-16`).
3. [Baixa] Revisar logs de suspensão para evitar divergências de cobrança.

## 5. Decisões de Auditoria
- Critério de match do app: pasta `nucleos/` (maior número de arquivos).
- Assunções documentadas: ausência de endpoint específico para listar núcleos do usuário.

## 6. Anexos (buscas e referências)
- Rotas API: `nucleos/api_urls.py`
- Templates analisados: `templates/nucleos/*.html`

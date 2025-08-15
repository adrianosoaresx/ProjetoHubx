# Auditoria de Requisitos — chat

**Escopo da sprint:** análise do app `chat` com base em `.requisitos/chat/**` e código em `chat/`.
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML, JavaScript
- Principais diretórios: `models.py`, `consumers.py`, `services.py`, `tasks.py`, `api_views.py`, `templates/chat/`
- Pontos de entrada/rotas: `chat/urls.py`, `chat/api_urls.py`, `chat/routing.py`
- Autenticação/Autorização: `login_required` nas views, permissões `IsChannelParticipant` e `IsChannelAdminOrOwner` em `api_views.py`

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | Comunicação em tempo real via WebSocket | ATENDIDO | `chat/routing.py:5-7`, `chat/consumers.py:31-63` | Baixo | — |
| RF-02 | Envio de mensagens multimídia | ATENDIDO | `chat/models.py:96-118`, `chat/consumers.py:72-104` | Baixo | — |
| RF-03 | Validação de escopo do usuário | ATENDIDO | `chat/consumers.py:42-58` | Baixo | — |
| RF-04 | Notificações em tempo real | ATENDIDO | `chat/consumers.py:118-120`, `chat/models.py:182-200` | Baixo | — |
| RF-05 | Permissões de administrador (fixar/exportar) | ATENDIDO | `chat/models.py:126-127`, `chat/api_urls.py:59-66` | Baixo | — |
| RF-06 | Mensagens encriptadas (E2EE) | ATENDIDO | `chat/models.py:40-47`, `chat/consumers.py:85-117` | Médio | Garantir gestão de chaves no cliente |
| RF-07 | Regras de retenção de mensagens | ATENDIDO | `chat/models.py:46-51`, `chat/tasks.py:47-74` | Médio | Monitorar volume de dados excluídos |
| RF-08 | Respostas e threads | ATENDIDO | `chat/models.py:119-125`, `chat/consumers.py:72-83` | Baixo | — |
| RF-09 | Favoritos e leitura de mensagens | ATENDIDO | `chat/models.py:133-134`, `chat/models.py:214-224` | Baixo | — |
| RF-10 | Detecção de spam | ATENDIDO | `chat/spam.py:12-40`, `chat/services.py:83-112` | Médio | Ajustar heurísticas conforme uso |
| RF-11 | Anexos e varredura de malware | ATENDIDO | `chat/models.py:227-244`, `chat/tasks.py:77-87` | Médio | Registrar resultados de scan |
| RF-12 | Integração com Agenda | ATENDIDO | `chat/services.py:128-175` | Médio | Revisar permissões na criação de itens |
| RF-13 | Resumos de chat | ATENDIDO | `chat/tasks.py:91-107`, `chat/models.py:302-309` | Baixo | — |
| RF-14 | Tópicos em alta | ATENDIDO | `chat/tasks.py:190-238`, `chat/models.py:285-299` | Baixo | — |
| RF-15 | Preferências de usuário | ATENDIDO | `chat/models.py:316-334`, `chat/api_urls.py:115` | Baixo | — |

### 2.1 Detalhes por requisito (com evidências)
**RF-01 — Comunicação em tempo real**  
- **Descrição:** suporte a WebSocket `ws/chat/<channel_id>/`.
- **Evidências:**
  - `chat/routing.py:5-7`
  - Trecho:
    ```python
    websocket_urlpatterns = [
        re_path(r"ws/chat/(?P<channel_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
    ]
    ```
  - `chat/consumers.py:31-63` valida conexão e adiciona usuário ao grupo.
- **Conclusão:** ATENDIDO  
- **Ação:** —

**RF-02 — Envio de mensagens multimídia**  
- **Descrição:** suporta tipos `text`, `image`, `video` e `file`.
- **Evidências:** `chat/models.py:96-118`, `chat/consumers.py:72-104`
- **Conclusão:** ATENDIDO  
- **Ação:** —

*(demais requisitos seguem conforme tabela)*

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** links para criar nova conversa e acessar detalhes presentes em `conversation_list.html` (`chat/templates/chat/conversation_list.html:10-16,24-44`).
- **Roteamento:** rotas web em `chat/urls.py` e APIs em `chat/api_urls.py` cobrem listagem, mensagens e moderação.
- **Acesso/Permissões:** views protegidas por `login_required`; APIs usam `permissions.IsAuthenticated` e classes específicas.
- **UI/Validações/Feedback:** formulários exibem mensagens de sucesso/erro em `views.py:26-38` e componentes de busca em `conversation_detail.html:42-56`.
- **I18n/A11y:** templates usam `{% trans %}` e atributos `aria-*` (ex.: `conversation_list.html:10-16`).
- **Links/ações quebradas:** não foram encontrados links quebrados durante a inspeção estática.
- **Cobertura de fluxos críticos:** envio de mensagens, reações, fixação e busca implementados em templates e serviços.
- **Resumo:** Prioridades 1) monitorar heurísticas de spam, 2) garantir política de retenção auditável, 3) documentar gestão de chaves para E2EE.

## 4. Gaps e Plano de Ação Priorizado
1. [Média] Validar gestão de chaves para E2EE — revisar documentação e suporte ao cliente.
2. [Média] Auditoria periódica da retenção de mensagens — criar relatório de exclusões.
3. [Baixa] Ajustar heurísticas de spam conforme métricas reais — ajustar limites via configuração.

## 5. Decisões de Auditoria
- Critério de match do app: pasta `chat/` com maior número de arquivos de código.
- Assunções documentadas: métricas de performance não verificadas em ambiente local.

## 6. Anexos (buscas e referências)
- `pytest tests/chat -q`


# Auditoria de Requisitos — notificacoes

**Escopo da sprint:** análise do app `notificacoes` com base em `.requisitos/notificacoes/**` e código em `notificacoes/`.  
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML
- Principais diretórios: `notificacoes/`, `notificacoes/templates/notificacoes`
- Pontos de entrada/rotas: `notificacoes/urls.py`, `notificacoes/api.py`, `notificacoes/routing.py`
- Autenticação/Autorização: decorators `login_required`, `permission_required` e `staff_member_required` nas views; permissões DRF e `CanSendNotifications` na API

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | Cadastro de modelos de notificação | ATENDIDO | `notificacoes/models.py:25-37`, `notificacoes/views.py:21-55`, `notificacoes/views.py:126-137` | Baixo | — |
| RF-02 | Preferências de notificação por usuário | PARCIAL | `notificacoes/services/notificacoes.py:48-56` | Médio | Implementar modelo dedicado ou documentar dependência do app `configuracoes` |
| RF-03 | Disparo de notificações via serviço interno | ATENDIDO | `notificacoes/services/notificacoes.py:31-76` | Baixo | — |
| RF-04 | Envio assíncrono com retentativas | ATENDIDO | `notificacoes/tasks.py:26-75` | Baixo | — |
| RF-05 | Registro de logs imutáveis | ATENDIDO | `notificacoes/models.py:43-70`, `notificacoes/views.py:57-96` | Baixo | — |
| RF-06 | Métricas Prometheus | PARCIAL | `notificacoes/services/metrics.py:4-24`, `notificacoes/views.py:140-167` | Médio | Incluir `templates_total` na view e assegurar cobertura de métricas | 
| RF-08 | Entrega em tempo real via WebSocket | ATENDIDO | `notificacoes/tasks.py:43-59`, `notificacoes/consumers.py:10-23`, `notificacoes/routing.py:1-7` | Baixo | — |
| RF-09 | Marcar notificação como lida | ATENDIDO | `notificacoes/api.py:25-52` | Baixo | — |
| RF-10 | CRUD de inscrições Web Push | ATENDIDO | `notificacoes/api.py:74-107`, `notificacoes/models.py:95-113` | Baixo | — |
| RF-11 | Resumos diário/semanal | ATENDIDO | `notificacoes/tasks.py:97-147`, `notificacoes/tasks.py:150-202` | Baixo | — |
| RF-12 | Permissão de disparo por endpoint | ATENDIDO | `notificacoes/api.py:55-70`, `notificacoes/permissions.py:1-8` | Baixo | — |

### 2.1 Detalhes por requisito (com evidências)
**RF-01 — Cadastro de modelos de notificação**  
- **Descrição:** CRUD de templates com proteção contra exclusão quando em uso.  
- **Evidências:** modelos e permissões definidos no ORM, views com decorators e mensagem de erro na exclusão.  
- **Conclusão:** ATENDIDO.  

**RF-02 — Preferências de notificação por usuário**  
- **Descrição:** app deve armazenar preferências de canais.  
- **Evidências:** serviço busca preferências via `get_user_preferences`, sem modelo próprio.  
- **Conclusão:** PARCIAL.  
- **Ação:** avaliar criação de `UserNotificationPreference` ou formalizar dependência externa.  

**RF-06 — Métricas Prometheus**  
- **Descrição:** expor contadores de envios e falhas, além de total de templates.  
- **Evidências:** métricas definidas em `services/metrics.py` e dashboard parcial; teste `test_metrics_dashboard` falhou pela ausência de `templates_total`.  
- **Conclusão:** PARCIAL.  
- **Ação:** incluir chave `templates_total` na view e validar testes.  

*(demais requisitos atendidos conforme tabela)*

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** rotas mapeadas em `urls.py` para templates, logs, histórico e métricas; templates HTML presentes (`templates_list.html`, `template_form.html`, `logs_list.html`, `historico_list.html`, `metrics.html`).
- **Roteamento:** URLs declaradas em `urls.py`; APIs REST em `api.py`; WebSocket em `routing.py`.
- **Acesso/Permissões:** decorators de autenticação e staff nas views; permissões DRF e custom `CanSendNotifications` na API.
- **UI/Validações/Feedback:** uso de `messages.success/error` nas operações de template e delete; paginação para logs e histórico.
- **I18n/A11y:** textos e mensagens com `gettext_lazy`; templates simples, sem avaliação de A11y aprofundada.
- **Links/ações quebradas:** não foram identificados links quebrados nos templates analisados.
- **Cobertura de fluxos críticos:** envio imediato, retentativas, exportação CSV de logs e emissão de métricas foram verificados.
- **Resumo:** Prioridades 1) completar métricas `templates_total`; 2) formalizar modelo de preferências; 3) revisar acessibilidade dos templates.

## 4. Gaps e Plano de Ação Priorizado
1. [Média] Métricas incompletas no dashboard → ajustar `metrics_dashboard` para fornecer `templates_total`.  
2. [Média] Ausência de modelo de preferências no app → definir estratégia (modelo próprio ou dependência externa).  
3. [Baixa] Revisar acessibilidade nos templates.

## 5. Decisões de Auditoria
- Critério de match do app: pasta `notificacoes/` foi única com maior quantidade de arquivos de código.  
- Assunções: preferências de usuário residem no app `configuracoes` e são acessadas via serviço.

## 6. Anexos (buscas e referências)
- Templates identificados: `find notificacoes/templates -maxdepth 2 -type f`  
- Execução de testes: `pytest tests/notificacoes -q`

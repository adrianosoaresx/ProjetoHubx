# Auditoria de Requisitos — agenda

**Escopo da sprint:** análise do app `agenda` com base em `.requisitos/agenda/**` e código em `agenda`.
**Data:** 2025-08-15
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML.
- Principais diretórios: `agenda/`, `agenda/templates/agenda/`.
- Pontos de entrada/rotas: `agenda/urls.py`, `agenda/api_urls.py`.
- Autenticação/Autorização: `LoginRequiredMixin` nas views e filtragem por organização/núcleo.

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|---------------|--------------------|
| RF-01 | CRUD de eventos com validação de endereço e orçamento | ATENDIDO | `agenda/models.py:167-206` | Baixo | — |
| RF-02 | Inscrição única com pagamento e lista de espera | ATENDIDO | `agenda/models.py:47-116` | Baixo | — |
| RF-03 | QR Code e check-in | ATENDIDO | `agenda/models.py:82-152`, `agenda/views.py:401-412` | Baixo | — |
| RF-04 | Materiais de divulgação com workflow | PARCIAL | `agenda/models.py:299-329`, `agenda/views.py:447-467` | Médio | Ajustar exibição na lista para mostrar apenas aprovados e status correto |
| RF-05 | Parcerias e avaliação de patrocinadores | ATENDIDO | `agenda/models.py:259-278`, `agenda/views.py:380-398` | Baixo | — |
| RF-06 | Fluxo de briefing com notificações | ATENDIDO | `agenda/models.py:342-360`, `agenda/tasks.py:44-49` | Baixo | — |
| RF-07 | Feedback pós-evento | ATENDIDO | `agenda/models.py:390-409` | Baixo | — |
| RF-08 | Controle de orçamento do evento | ATENDIDO | `agenda/models.py:200-202`, `agenda/views.py:360-366` | Baixo | — |
| RF-09 | Capacidade e promoção da lista de espera | ATENDIDO | `agenda/models.py:98-111`, `agenda/tasks.py:13-26` | Baixo | — |
| RF-10 | Tarefas e logs de auditoria | ATENDIDO | `agenda/models.py:411-471` | Baixo | — |

### 2.1 Detalhes por requisito (com evidências)
**RF-01 — CRUD de eventos**  
- **Descrição:** criação e edição de eventos com validação de cidade, UF e CEP.  
- **Evidências:** `agenda/models.py:167-185`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-02 — Inscrição de usuários**  
- **Descrição:** inscrição única por evento, pagamento opcional e lista de espera.  
- **Evidências:** `agenda/models.py:47-116`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-03 — QR Code e check-in**  
- **Descrição:** gera QR code ao confirmar inscrição e validação via API.  
- **Evidências:** `agenda/models.py:144-152`, `agenda/views.py:401-412`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-04 — Materiais de divulgação**  
- **Descrição:** upload com aprovação/devolução e filtro para usuários comuns.  
- **Evidências:** `agenda/models.py:299-329`, `agenda/views.py:447-463`, `agenda/forms.py:97-121`.  
- **Conclusão:** PARCIAL (teste indica listagem incorreta).  
- **Ação:** corrigir template de listagem e garantir exibição somente de aprovados.

**RF-05 — Parcerias**  
- **Descrição:** cadastro de parcerias com avaliação única.  
- **Evidências:** `agenda/models.py:259-278`, `agenda/views.py:380-398`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-06 — Briefing de eventos**  
- **Descrição:** fluxo rascunho → orçamentado → aprovado/recusado com notificação.  
- **Evidências:** `agenda/models.py:342-360`, `agenda/tasks.py:44-49`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-07 — Avaliação de eventos**  
- **Descrição:** participantes confirmados avaliam eventos pós-término.  
- **Evidências:** `agenda/models.py:390-409`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-08 — Controle de orçamento**  
- **Descrição:** campos de orçamento com log de alterações.  
- **Evidências:** `agenda/models.py:200-202`, `agenda/views.py:360-366`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-09 — Lista de espera**  
- **Descrição:** promove inscritos pendentes via tarefa Celery.  
- **Evidências:** `agenda/models.py:98-111`, `agenda/tasks.py:13-26`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

**RF-10 — Tarefas e logs**  
- **Descrição:** tarefas vinculadas a mensagens do chat com histórico.  
- **Evidências:** `agenda/models.py:411-471`.  
- **Conclusão:** ATENDIDO.  
- **Ação:** —.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** links para parcerias renderizados (`agenda/templates/agenda/parceria_list.html:1-33`).
- **Roteamento:** rotas web e API mapeadas (`agenda/urls.py:27-82`).
- **Acesso/Permissões:** filtragem por organização/núcleo nas listagens (`agenda/views.py:453-461`).
- **UI/Validações/Feedback:** validação de arquivos no formulário (`agenda/forms.py:97-121`).
- **I18n/A11y:** uso de `{% trans %}` nos templates (`agenda/templates/agenda/parceria_list.html:4-33`).
- **Links/ações quebradas:** erro de `DATE_FORMAT` no calendário causa falha nos testes (`tests/agenda/test_views.py::test_eventos_por_dia_view_com_evento`).
- **Cobertura de fluxos críticos:** check-in via QR code (`agenda/views.py:401-412`).
- **Resumo:** Prioridades 1) corrigir `DATE_FORMAT` nos templates, 2) ajustar listagem de materiais, 3) revisar migração de `avaliacao` em `InscricaoEvento`.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Templates do calendário dependem de `DATE_FORMAT` → incluir variável no contexto ou usar formato padrão.
2. [Média] `MaterialDivulgacaoEventoListView` deve exibir apenas materiais aprovados e informar status.
3. [Média] Ajustar migração de `InscricaoEvento.avaliacao` conforme falha de teste.

## 5. Decisões de Auditoria
- Critério de match do app: único diretório `agenda` continha maior volume de código relacionado.
- Assunções: recursos de pagamento e logging foram considerados parte do escopo atual.

## 6. Anexos (buscas e referências)
- Execução de testes: `pytest tests/agenda -q` (5 falhas, 35 passes)【8e1d8b†L128-L134】.

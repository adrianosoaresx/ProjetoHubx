# Auditoria de Requisitos — accounts

**Escopo da sprint:** análise do app `accounts` com base em `.requisitos/accounts/**` e código em `accounts`.  
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML (Django templates)
- Principais diretórios: `accounts/`, `accounts/templates/`
- Pontos de entrada/rotas: `accounts/urls.py`
- Autenticação/Autorização: backend customizado `EmailBackend`, decorators `login_required`, suporte a 2FA via TOTP

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| REQ-001 | Cadastro com confirmação de e-mail | ATENDIDO | `accounts/forms.py:62-75`, `accounts/views.py:385-405` | Baixo | — |
| REQ-002 | Login e logout | ATENDIDO | `accounts/views.py:269-283` | Baixo | — |
| REQ-003 | Recuperação de senha por e-mail | ATENDIDO | `accounts/views.py:326-372` | Baixo | — |
| REQ-004 | Edição de perfil com avatar/capa/biografia | ATENDIDO | `accounts/views.py:54-68`, `accounts/templates/perfil/informacoes_pessoais.html:1-33` | Baixo | — |
| REQ-005 | Validação de e-mail único | ATENDIDO | `accounts/forms.py:38-42`, `accounts/models.py:106-112` | Baixo | — |
| REQ-006 | Confirmação de e-mail expira em 24h e reenvio | ATENDIDO | `accounts/forms.py:70-75`, `accounts/views.py:433-447` | Médio | Revisar testes de expiração |
| REQ-007 | Limite de 3 tentativas de login (bloqueio 15min) | ATENDIDO | `accounts/backends.py:41-44` | Baixo | — |
| REQ-008 | Exclusão de conta com soft delete e purga 30d | ATENDIDO | `accounts/views.py:286-306`, `accounts/tasks.py:38-43` | Médio | Garantir agendamento do task |
| REQ-009 | Autenticação em duas etapas (2FA) | ATENDIDO | `accounts/views.py:111-145` | Baixo | — |
| REQ-010 | Registro multietapas via token de convite | ATENDIDO | `accounts/views.py:453-520` | Médio | Documentar UX das etapas |
| REQ-011 | Conexões sociais (listar/remover) | ATENDIDO | `accounts/models.py:228-235`, `accounts/views.py:178-199` | Baixo | — |
| REQ-012 | Upload e gerenciamento de mídias com tags | ATENDIDO | `accounts/models.py:289-300`, `accounts/forms.py:189-208` | Médio | Monitorar tamanho de arquivos |
| REQ-013 | Redes sociais armazenadas em JSON | ATENDIDO | `accounts/forms.py:165-188` | Baixo | — |
| REQ-014 | Registro de eventos de segurança | ATENDIDO | `accounts/models.py:335-342`, `accounts/views.py:92-97` | Baixo | — |
| REQ-015 | API REST para operações de conta | ATENDIDO | `accounts/api.py:30-150` | Baixo | — |

### 2.1 Detalhes por requisito (com evidências)
**REQ-001 — Cadastro com confirmação de e-mail**  
- **Descrição:** Usuário se cadastra com e-mail e senha; conta ativada após confirmação.
- **Evidências:**
  - `accounts/forms.py:62-75`
  - `accounts/views.py:385-405`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-002 — Login e logout**  
- **Descrição:** Autenticação com email e senha; logout encerra sessão.
- **Evidências:**
  - `accounts/views.py:269-283`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-003 — Recuperação de senha por e-mail**  
- **Descrição:** Token de 1h enviado por e-mail para redefinição de senha.
- **Evidências:**
  - `accounts/views.py:326-372`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-004 — Edição de perfil com avatar/capa/biografia**  
- **Descrição:** Usuário atualiza dados pessoais e imagens.
- **Evidências:**
  - `accounts/views.py:54-68`
  - `accounts/templates/perfil/informacoes_pessoais.html:1-33`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-005 — Validação de e-mail único**  
- **Descrição:** E-mails duplicados são rejeitados.
- **Evidências:**
  - `accounts/forms.py:38-42`
  - `accounts/models.py:106-112`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-006 — Confirmação de e-mail expira em 24h e reenvio**  
- **Descrição:** Token de confirmação expira em 24h com opção de reenvio.
- **Evidências:**
  - `accounts/forms.py:70-75`
  - `accounts/views.py:433-447`
- **Conclusão:** ATENDIDO  
- **Ação:** revisar cobertura de testes para expiração.

**REQ-007 — Limite de 3 tentativas de login**  
- **Descrição:** Bloqueia conta por 15 minutos após 3 falhas.
- **Evidências:**
  - `accounts/backends.py:41-44`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-008 — Exclusão de conta com purga após 30 dias**  
- **Descrição:** Soft delete imediato e remoção definitiva após 30 dias.
- **Evidências:**
  - `accounts/views.py:286-306`
  - `accounts/tasks.py:38-43`
- **Conclusão:** ATENDIDO  
- **Ação:** garantir execução periódica do task de purga.

**REQ-009 — Autenticação em duas etapas (2FA)**  
- **Descrição:** Usuário habilita ou desabilita 2FA com TOTP.
- **Evidências:**
  - `accounts/views.py:111-145`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-010 — Registro multietapas via token de convite**  
- **Descrição:** Processo de cadastro dividido em etapas iniciadas por token.
- **Evidências:**
  - `accounts/views.py:453-520`
- **Conclusão:** ATENDIDO  
- **Ação:** documentar UX das etapas.

**REQ-011 — Conexões sociais**  
- **Descrição:** Listar conexões e remover contato.
- **Evidências:**
  - `accounts/models.py:228-235`
  - `accounts/views.py:178-199`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-012 — Upload e gerenciamento de mídias com tags**  
- **Descrição:** Envio, validação, edição e exclusão de mídias.
- **Evidências:**
  - `accounts/models.py:289-300`
  - `accounts/forms.py:189-208`
- **Conclusão:** ATENDIDO  
- **Ação:** monitorar tamanho de arquivos.

**REQ-013 — Redes sociais em JSON**  
- **Descrição:** Armazenamento e edição de links de redes sociais em JSON.
- **Evidências:**
  - `accounts/forms.py:165-188`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-014 — Registro de eventos de segurança**  
- **Descrição:** Eventos sensíveis gravados com IP e timestamp.
- **Evidências:**
  - `accounts/models.py:335-342`
  - `accounts/views.py:92-97`
- **Conclusão:** ATENDIDO  
- **Ação:** —

**REQ-015 — API REST de contas**  
- **Descrição:** Endpoints para confirmar e-mail, resetar senha, 2FA e exclusão.
- **Evidências:**
  - `accounts/api.py:30-150`
- **Conclusão:** ATENDIDO  
- **Ação:** —

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** links para recuperação de senha e cadastro no template de login [`accounts/templates/login/login.html:64-78`].
- **Roteamento:** rotas completas definidas em `accounts/urls.py` [`accounts/urls.py:7-61`].
- **Acesso/Permissões:** uso de `@login_required` nas views de perfil [`accounts/views.py:49-72`]; API requer autenticação condicional [`accounts/api.py:25-28`].
- **UI/Validações/Feedback:** mensagens de sucesso/erro via `messages` [`accounts/views.py:54-68`, `accounts/views.py:286-306`].
- **I18n/A11y:** templates utilizam `{% trans %}` e atributos ARIA [`accounts/templates/login/login.html:1-33`].
- **Links/ações quebradas:** não encontrados.
- **Cobertura de fluxos críticos:** cadastro, confirmação de e-mail, login/2FA e exclusão de conta exercitados em views e API.
- **Resumo:** Prioridades 1) garantir agendamento do purge de contas; 2) testar expiracão de tokens; 3) documentar UX do registro multietapas.

## 4. Gaps e Plano de Ação Priorizado
1. [Média] Verificar agendamento do task `purge_soft_deleted` para garantir exclusão definitiva em produção.
2. [Média] Ampliar testes automatizados para cobrir expiração de tokens de confirmação de e-mail.
3. [Baixa] Documentar e validar experiência do usuário nas etapas do registro multietapas.

## 5. Decisões de Auditoria
- Critério de match do app: selecionado diretório `accounts` na raiz por ser único e conter maior quantidade de arquivos de código.
- Assunções documentadas: considerou-se que tarefas Celery são executadas conforme configuração externa.

## 6. Anexos (buscas e referências)
- `pytest tests/accounts -q` (32 testes executados)
- Levantamento de templates em `accounts/templates/`

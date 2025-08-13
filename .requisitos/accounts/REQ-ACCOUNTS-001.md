---
id: REQ-ACCOUNTS-001
title: Requisitos Accounts Hubx
module: accounts
status: Em vigor
version: "1.1.0"
authors: [preencher@hubx.space]
created: "2025-07-25"
updated: "2025-08-13"
owners: [preencher]
reviewers: [preencher]
tags: [backend]
related_docs: []
dependencies: []
---

## 1. Visão Geral
O App Accounts gerencia todo o ciclo de vida de contas de usuário no sistema Hubx. Além do cadastro, autenticação e gerenciamento de perfil, o módulo implementa:

- **Fluxo multietapas de registro** baseado em tokens de convite que definem o tipo de usuário e, opcionalmente, o núcleo de organização. O usuário fornece CPF, nome completo, nome de usuário, e‑mail, senha e foto de perfil e aceita os termos para finalizar o cadastro.
- **Gestão de tentativas de login** com contadores de falhas e bloqueio temporário após número excessivo de tentativas.
- **Autenticação em duas etapas (2FA)** opcional usando códigos TOTP (Google Authenticator ou similares).
- **Conexões sociais** entre usuários (amizades/seguidores), permitindo listar e remover conexões.
- **Upload e gerenciamento de arquivos de mídia** (imagens, vídeos, PDFs) com tags, incluindo validação de extensão e tamanho.
- **Auditoria de segurança**, registrando tentativas de login e eventos relevantes (confirmação de e‑mail, reset de senha, ativação/desativação de 2FA, exclusão de conta).

## 2. Escopo

- **Inclui**:
  - Cadastro de usuário (fluxo multietapas com CPF, nome completo, e‑mail, senha e foto)
  - Confirmação de e‑mail com token de 24 h e reenvio de confirmação
  - Autenticação (login/logout) com limite de tentativas e suporte opcional a 2FA
  - Recuperação de senha via e‑mail com token expirável em 1 h
  - Edição de perfil (nome, CPF, e‑mail, avatar, capa, biografia e contatos)
  - Gestão de permissões lógicas por tipo de usuário (root, admin, coordenador, nucleado, associado, convidado)
  - Exclusão de conta com soft delete e purga após 30 dias
  - Conexões sociais (listar e remover conexões)
  - Upload, listagem, edição e exclusão de mídias com tags
  - Armazenamento e edição de redes sociais em formato JSON
  - Registro de tentativas de login e eventos de segurança
  - API REST para operações de conta (confirmação de e‑mail, reset de senha, 2FA, exclusão/cancelamento)
- **Exclui**:
  - Gestão de organizações, núcleos ou eventos além da vinculação inicial via token
  - Funcionalidades de rede social avançadas (envio de solicitações de conexão, feed de atividades)
  - Processamento de pagamentos ou assinaturas

## 3. Requisitos Funcionais

- **RF-01**
  - Descrição: Usuário pode se cadastrar com e‑mail e senha, gerando conta ativa após confirmar o e‑mail.
  - Prioridade: Alta
  - Critérios de Aceite: E‑mail único; senha atende política de segurança; token de confirmação enviado.
- **RF-02**
  - Descrição: Usuário pode realizar login e logout no sistema.
  - Prioridade: Alta
  - Critérios de Aceite: Sessão válida; logout remove token ou sessão.
- **RF-03**
  - Descrição: Usuário pode recuperar senha via e‑mail com token expirável em 1 hora.
  - Prioridade: Média
  - Critérios de Aceite: Link enviado; token inválido após 1 h.
- **RF-04**
  - Descrição: Usuário pode editar perfil incluindo avatar, capa e biografia.
  - Prioridade: Média
  - Critérios de Aceite: Uploads compatíveis; campos salvos.
- **RF-05**
  - Descrição: Validação de e‑mail único globalmente.
  - Prioridade: Alta
  - Critérios de Aceite: Tentativa de usar e‑mail existente retorna erro.
- **RF-06**
  - Descrição: Confirmação de e‑mail deve ocorrer em até 24 horas após cadastro. Após expirar, o token é invalidado e o usuário deve solicitar nova confirmação.
  - Prioridade: Média
  - Critérios de Aceite: Token expirado gera erro; reenvio disponível.
- **RF-07**
  - Descrição: Limitar tentativas de login a 3. Após 3 falhas consecutivas, a conta é bloqueada por 15 minutos.
  - Prioridade: Alta
  - Critérios de Aceite: Nova tentativa durante bloqueio deve falhar; contador é resetado em login bem‑sucedido ou reset de senha.
- **RF-08**
  - Descrição: Permitir remoção de conta pelo usuário com soft delete. Conta fica em estado “pendente_de_exclusao” por 30 dias antes de remoção permanente.
  - Prioridade: Média
  - Critérios de Aceite: Excluir conta requer confirmação textual; usuário fica inativo imediatamente; cancelamento possível; purga executada após 30 dias.
- **RF-09**
  - Descrição: Suporte a autenticação em duas etapas (2FA) opcional com códigos TOTP.
  - Prioridade: Média
  - Critérios de Aceite: Usuário pode habilitar/desabilitar 2FA; login exige código TOTP quando habilitado; QR code fornecido; segredo armazenado de forma segura.
- **RF-10** – **Registro multietapas** – O processo de cadastro deve ser dividido em etapas (nome de usuário, nome completo, CPF, e‑mail, senha e foto), iniciadas a partir de um **token de convite**. O token define o tipo de usuário (admin, coordenador, nucleado, associado ou convidado) e o núcleo inicial. O usuário deve aceitar os termos de uso antes da criação da conta.
  - Prioridade: Média
  - Critérios de Aceite: Todas as etapas devem validar dados obrigatórios (e‑mail único, CPF válido, senha forte); sem token válido, cadastro é bloqueado.
- **RF-11** – **Gerenciamento de conexões** – Usuário pode visualizar suas conexões e remover um contato existente. A funcionalidade de solicitação/adicionamento de conexão poderá ser implementada futuramente.
  - Prioridade: Baixa
  - Critérios de Aceite: Lista exibe conexões atuais; ao remover, a conexão é excluída e usuário é notificado.
- **RF-12** – **Upload e gerenciamento de mídias** – Usuário pode enviar arquivos de mídia (imagens, vídeos, PDFs), adicionar descrição e tags, pesquisar mídias por descrição ou tags, editar ou remover mídias.
  - Prioridade: Média
  - Critérios de Aceite: Tipos de arquivo devem estar em lista permitida; tamanho não pode exceder o valor configurado; tags são separadas por vírgula e armazenadas em objeto `MediaTag`; ao excluir, o arquivo é removido.
- **RF-13** – **Redes sociais em JSON** – Usuário pode cadastrar e editar links de redes sociais armazenados em campo JSON, usando formulário dedicado.
  - Prioridade: Baixa
  - Critérios de Aceite: Dados devem ser JSON válido; campos ausentes resultam em objeto vazio.
- **RF-14** – **Registro de eventos de segurança** – O sistema deve registrar eventos como confirmação de e‑mail, redefinição de senha, ativação/desativação de 2FA, alteração de senha e exclusão de conta, armazenando data/hora e IP.
  - Prioridade: Média
  - Critérios de Aceite: Cada evento sensível gera registro com identificação do usuário, IP e timestamp; registros são persistidos para auditoria.
- **RF-15** – **API REST de contas** – Disponibilizar endpoints HTTP para operações de gerenciamento de conta (confirmação de e‑mail, reenvio de confirmação, solicitação e redefinição de senha, ativação/desativação de 2FA, exclusão de conta e cancelamento de exclusão).
  - Prioridade: Média
  - Critérios de Aceite: Endpoints retornam códigos de status adequados e mensagens de erro; autenticação é exigida quando necessário.
- **RF-16** – Adicionar funcionalidade de envio/solicitação de conexões e feed de atividades do usuário.

## 4. Requisitos Não Funcionais

### Performance
- **RNF-02** — Respostas de login e cadastro devem ter p95 ≤ 200 ms; métrica/meta: 200 ms.

### Segurança & LGPD
- **RNF-01** — Senhas armazenadas com bcrypt (mínimo 12 rounds); tempo de hash ≤ 500 ms.
- **RNF-06** — Tokens de recuperação e confirmação devem ter entropia ≥ 128 bits e expirar em 24 horas.
- **RNF-08** — Validação de mídias — mídias enviadas devem obedecer às restrições configuráveis de extensão (`USER_MEDIA_ALLOWED_EXTS`) e tamanho (`USER_MEDIA_MAX_SIZE`, padrão 50 MB); arquivos fora do padrão são rejeitados com mensagem clara.
- **RNF-09** — Proteção do segredo de 2FA — o segredo TOTP (`two_factor_secret`) deve ser armazenado cifrado e nunca retornado ao cliente após a ativação.

### Observabilidade
- **RNF-07** — Logs de tentativas de login e eventos de segurança devem ser armazenados com carimbo de data/hora e IP.
- **RNF-10** — Auditoria e relatórios — disponibilizar relatórios de uso e logs de segurança para administradores.

### Arquitetura & Escala
- **RNF-03** — Suportar 1 000 cadastros por hora; métrica/meta: escalonamento automático.
- **RNF-04** — Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`), garantindo consistência e evitando campos manuais.
- **RNF-05** — Quando houver necessidade de exclusão lógica, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando os campos `deleted` e `deleted_at`.

## 5. Casos de Uso

### UC-01 – Criar Conta (Onboarding)
1. Usuário inicia cadastro a partir de um **token de convite**.
2. Informa nome de usuário, nome completo, CPF e e‑mail.
3. Define e confirma a senha; sistema valida a força.
4. (Opcional) Faz upload de foto de perfil.
5. Aceita os termos de uso.
6. Sistema cria conta inativa, associa tipo de usuário e núcleo conforme o token e envia e‑mail de confirmação com validade de 24 h.
7. Cenário de erro: token inválido ou expirado → mensagem de erro.

### UC-02 – Confirmar E‑mail
1. Usuário clica no link de confirmação recebido por e‑mail.
2. Sistema valida o token e ativa a conta se válido.
3. Sistema grava evento de segurança “email_confirmado”.
4. Cenário de erro: token inexistente, expirado ou já utilizado → tela de erro, opção de reenviar confirmação.

### UC-03 – Login
1. Usuário fornece e‑mail e senha (e código TOTP se 2FA estiver habilitado).
2. Sistema valida credenciais.
3. Se falhar, incrementa contador de `failed_login_attempts` e registra `LoginAttempt` com IP.
4. Após três falhas consecutivas, bloqueia conta por 15 min.
5. Em caso de sucesso, zera contador de falhas, limpa bloqueio e registra tentativa bem‑sucedida.

### UC-04 – Recuperar Senha
1. Usuário solicita redefinição informando e‑mail.
2. Sistema gera token de 1 h e envia link de redefinição.
3. Usuário define nova senha; sistema valida e atualiza credenciais.
4. Zera contador de falhas e desbloqueia conta.
5. Cenário de erro: token expirado ou inexistente → solicitar novo envio.

### UC-05 – Editar Perfil
1. Usuário autenticado acessa página de perfil.
2. Atualiza campos desejados (nome, e‑mail, CPF, avatar, capa, biografia, endereço, telefone, redes sociais).
3. Sistema valida dados (unicidade de e‑mail/CPF, JSON válido para redes sociais).
4. Se e‑mail for alterado, conta é marcada como inativa e novo e‑mail de confirmação é enviado.
5. Sistema salva alterações e exibe mensagem de sucesso.

### UC-06 – Ativar/Desativar 2FA
1. Usuário solicita ativação; sistema gera segredo TOTP e apresenta QR code.
2. Usuário escaneia QR code e informa código TOTP para confirmar ativação.
3. Sistema grava segredo cifrado e marca `two_factor_enabled` como verdadeiro.
4. Para desativar, sistema solicita código TOTP atual e, se válido, remove o segredo e desativa 2FA.

### UC-07 – Gerenciar Mídias
1. Usuário acessa lista de mídias; pode filtrar por descrição ou tags.
2. Para enviar, seleciona arquivo (imagem, vídeo ou PDF), adiciona descrição e tags separadas por vírgula.
3. Sistema valida tipo e tamanho do arquivo; se válido, salva mídia e tags.
4. Usuário pode editar descrição/tags ou excluir o arquivo.
5. Cenário de erro: arquivo de tipo não permitido ou maior que o limite → rejeitar upload e mostrar mensagem.

### UC-08 – Gerenciar Conexões
1. Usuário acessa lista de conexões.
2. Pode remover uma conexão existente, com confirmação.
3. Sistema atualiza relação many‑to‑many e exibe mensagem de sucesso.

### UC-09 – Excluir Conta
1. Usuário acessa a opção de exclusão de conta.
2. Informa confirmação textual (por exemplo, digitar “EXCLUIR”).
3. Sistema marca a conta como excluída (`deleted=True`, `is_active=False`), grava evento de segurança “conta_excluida” e encerra sessão.
4. A conta permanece pendente de exclusão por 30 dias, permitindo cancelamento via API.
5. Após 30 dias, o task de purga remove permanentemente os dados.

## 6. Regras de Negócio

- E‑mail deve ser único e confirmado antes de ativar conta.
- CPF, se informado, deve ser único e válido segundo o formato brasileiro.
- Apenas usuários ativos podem autenticar; alteração de e‑mail reativa o estado inativo até nova confirmação.
- Após três tentativas de login sem sucesso, a conta entra em bloqueio temporário de 15 minutos.
- O token de confirmação de e‑mail expira em 24 horas; após expirar, o usuário deve solicitar novo envio.
- O token de redefinição de senha expira em 1 hora.
- O processo de exclusão de conta deve solicitar confirmação e aguardar 30 dias antes da eliminação definitiva; o usuário pode cancelar dentro desse período.
- Para ativar ou desativar 2FA, é obrigatório informar um código TOTP válido.

## 7. Modelo de Dados

*Nota:* Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário. Assim, campos de timestamp e exclusão lógica não são listados individualmente.

### accounts.User
Descrição: ...
Campos:
- `id`: UUID
- `email`: EmailField — único
- `username`: CharField
- `password_hash`: string
- `is_active`: boolean
- `email_confirmed`: boolean
- `failed_login_attempts`: integer
- `lock_expires_at`: datetime
- `two_factor_enabled`: boolean
- `two_factor_secret`: string — criptografado
- `exclusao_confirmada`: boolean
- `nome_completo`: string
- `cpf`: string — único
- `avatar`: FileField
- `cover`: FileField
- `biografia`: string
- `endereco`: string
- `cidade`: string
- `estado`: string
- `cep`: string
- `fone`: string
- `whatsapp`: string
- `redes_sociais`: JSON
- `perfil_publico`: boolean
- `mostrar_email`: boolean
- `mostrar_telefone`: boolean
- `user_type`: enum — {root, admin, coordenador, nucleado, associado, convidado}
- `organizacao`: ForeignKey → Organizacao
- `nucleo`: ForeignKey → Nucleo — opcional
- `connections`: ManyToMany → User — auto-referencial
- `followers`: ManyToMany → User — auto-referencial, assimétrico
Constraints adicionais:
- ...
Índices adicionais:
- ...

### accounts.AccountToken
Descrição: ...
Campos:
- `codigo`: string — token de alta entropia
- `tipo`: enum — {email_confirmation, password_reset}
- `usuario`: ForeignKey → User
- `expires_at`: datetime
- `used_at`: datetime — nullable
- `ip_gerado`: GenericIPAddressField — nullable
Constraints adicionais:
- ...
Índices adicionais:
- ...

### accounts.LoginAttempt
Descrição: ...
Campos:
- `usuario`: ForeignKey → User — nullable
- `email`: string
- `sucesso`: boolean
- `ip`: GenericIPAddressField — nullable
Constraints adicionais:
- ...
Índices adicionais:
- ...

### accounts.SecurityEvent
Descrição: ...
Campos:
- `usuario`: ForeignKey → User
- `evento`: string — ex.: `email_confirmado`, `senha_redefinida`, `2fa_habilitado`, `conta_excluida`
- `ip`: GenericIPAddressField — nullable
Constraints adicionais:
- ...
Índices adicionais:
- ...

### accounts.MediaTag
Descrição: ...
Campos:
- `nome`: string — único
Constraints adicionais:
- ...
Índices adicionais:
- ...

### accounts.UserMedia
Descrição: ...
Campos:
- `user`: ForeignKey → User
- `file`: FileField
- `descricao`: string
- `tags`: ManyToMany → MediaTag
Constraints adicionais:
- ...
Índices adicionais:
- ...

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Gerenciamento de contas
  Scenario: Usuário cria conta com sucesso
    Given um token de convite válido
    And etapas de cadastro preenchidas corretamente (nome, CPF, e‑mail, senha, termos)
    When envio os dados com e‑mail exclusivo
    Then a conta é criada inativa e um e‑mail de confirmação é enviado

  Scenario: Três falhas de login bloqueiam a conta
    Given um usuário ativo com e‑mail e senha cadastrados
    When tento logar com senha incorreta três vezes seguidas
    Then o sistema bloqueia a conta por 15 minutos

  Scenario: Usuário habilita 2FA
    Given usuário autenticado sem 2FA
    When solicito ativação e escaneio o QR code gerado
    And envio o código TOTP correto
    Then o 2FA é habilitado e registrado
```

## 9. Dependências e Integrações

- **Email Service**: envio de confirmação e reset (SMTP/Celery).
- **Cache (Redis)**: armazenamento de tokens de sessão e lockout de login.
- **OAuth2 / LDAP**: futuros métodos de login social.
- **Celery & RabbitMQ**: envio assíncrono de e‑mails e execução de tarefas programadas (purgar contas excluídas).
- **Sentry**: monitoramento de erros em produção.
- **pyotp**: geração e verificação de códigos TOTP para 2FA.
- **qrcode**: geração de QR codes para configuração de 2FA.
- **phonenumber-field**: validação de números de telefone.

## Anexos e Referências

- ...

## Changelog

- 1.1.0 — 2025-08-13 — Normalização para Padrão Unificado v3.1

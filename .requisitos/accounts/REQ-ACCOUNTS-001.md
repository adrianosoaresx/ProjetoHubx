---
id: REQ-ACCOUNTS-001
title: Requisitos Accounts Hubx
module: Accounts
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source: Requisitos_Accounts_Hubx.pdf
---

## 1. Visão Geral

O App Accounts gerencia todo o ciclo de vida de contas de usuário no sistema Hubx, incluindo registro, autenticação, gerenciamento de perfil, permissões e integrações externas.

## 2. Escopo
- **Inclui**:
  - Cadastro de usuário (email e senha)  
  - Autenticação (login/logout)  
  - Recuperação de senha via email  
  - Edição de perfil (nome, CPF, email, avatar, capa, biografia e contatos)  
  - Gestão de permissões lógicas por tipo de usuário  
- **Exclui**:
  - Gestão de organizações, núcleos ou eventos  

## 3. Requisitos Funcionais
- **RF-01**  
  - Descrição: Usuário pode se cadastrar com email e senha, gerando conta ativa.  
  - Prioridade: Alta  
  - Critérios de Aceite: Email único; senha atende política de segurança.  

- **RF-02**  
  - Descrição: Usuário pode realizar login e logout no sistema.  
  - Prioridade: Alta  
  - Critérios de Aceite: Sessão válida; logout remove token.  

- **RF-03**  
  - Descrição: Usuário pode recuperar senha via email com token expirável em 1 hora.  
  - Prioridade: Média  
  - Critérios de Aceite: Link enviado; token inválido após 1h.  

- **RF-04**  
  - Descrição: Usuário pode editar perfil incluindo avatar, capa e biografia.  
  - Prioridade: Média  
  - Critérios de Aceite: Uploads compatíveis; campos salvos.  

- **RF-05**  
  - Descrição: Validação de email único globalmente.  
  - Prioridade: Alta  
  - Critérios de Aceite: Tentativa de usar email existente retorna erro.  

## 4. Requisitos Não-Funcionais
- **RNF-01**  
  - Categoria: Segurança  
  - Descrição: Senhas armazenadas com bcrypt (mínimo 12 rounds)  
  - Métrica/Meta: Tempo de hash ≤ 500 ms  

- **RNF-02**  
  - Categoria: Desempenho  
  - Descrição: Respostas de login e cadastro devem ter p95 ≤ 200 ms  
  - Métrica/Meta: 200 ms  

- **RNF-03**  
  - Categoria: Escalabilidade  
  - Descrição: Suportar 1000 cadastros por hora  
  - Métrica/Meta: escalonamento automático  

## 5. Casos de Uso
### UC-01 – Criar Conta
1. Usuário acessa formulário de registro.  
2. Preenche email, senha e confirmação.  
3. Sistema valida dados e cria conta inativa.  
4. Envia email de confirmação com token de 1h.  
5. Usuário confirma email e conta é ativada.  
6. **Cenário de Erro**: email já cadastrado → mensagem de erro.

### UC-02 – Recuperar Senha
1. Usuário solicita recuperação informando email.  
2. Sistema envia email com link de reset (token 1h).  
3. Usuário redefine senha no link.  
4. **Cenário de Erro**: token expirado → solicitação de novo link.

### UC-03 – Editar Perfil
1. Usuário navega até página de perfil.  
2. Atualiza campos desejados (nome, avatar, cover, etc.).  
3. Sistema valida e salva alterações.  
4. **Cenário de Erro**: arquivo de imagem inválido → rejeitar.

## 6. Regras de Negócio
- Email deve ser único e confirmado antes de ativar conta.  
- Apenas usuários ativos podem autenticar.  
- Perfis de usuário seguem lógica: root, admin, associado, nucleado, coordenador, convidado.

## 7. Modelo de Dados
- **Account**  
  - id: UUID  
  - email: EmailField, único  
  - password_hash: string  
  - is_active: boolean  
  - last_login: datetime  
  - created_at, updated_at: datetime  

- **Profile**  
  - user: FK → Account.id  
  - nome_completo: string  
  - cpf: string (unique)  
  - avatar: ImageField (opcional)  
  - cover: ImageField (opcional)  
  - biografia: TextField  
  - endereco, estado, cep, fone, whatsapp: string  
  - redes_sociais: JSONField (opcional)  

- **Permission**  
  - user: FK → Account.id  
  - name: string  
  - granted_at: datetime  

- **AuthToken**  
  - token: string  
  - user: FK → Account.id  
  - type: enum ('email_confirmation','password_reset')  
  - expires_at: datetime  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Gerenciamento de contas
  Scenario: Usuário cria conta com sucesso
    Given formulário de registro válido
    When envio dados com email exclusivo
    Then conta é criada e email de confirmação é enviado
```

## 9. Dependências / Integrações
- **Email Service**: envio de confirmação e reset (SMTP/Celery).  
- **Cache (Redis)**: tokens de sessão e lockout de login.  
- **OAuth2 / LDAP**: futuros métodos de login social.  
- **Celery & RabbitMQ**: envio assíncrono de emails.  
- **Sentry**: monitoramento de erros em produção.

## 10. Anexos e Referências
- Documento fonte: Requisitos_Accounts_Hubx.pdf


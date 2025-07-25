---
id: REQ-CONFIGURACOES_CONTA-001
title: Requisitos Configurações de Conta Hubx
module: Configuracoes_Conta
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source: Requisitos_Configuracoes_Conta_Hubx.pdf
---

## 1. Visão Geral

O App de Configurações de Conta permite que cada usuário personalize suas preferências de notificação e aparência da interface de forma centralizada e persistente.

## 2. Escopo
- **Inclui**:
  - Gerenciamento de preferências de notificação (email, WhatsApp).  
  - Alternância de tema (claro/escuro).  
  - Visualização e edição das configurações pessoais.  
- **Exclui**:
  - Cadastro e autenticação (delegado a App Accounts).  
  - Configurações de organização, núcleo ou evento.

## 3. Requisitos Funcionais

- **RF-01**
  - Descrição: Usuário pode ativar/desativar notificação por email.
  - Prioridade: Alta
  - Critérios de Aceite: Checkbox salva e reflete estado atual.

- **RF-02**
  - Descrição: Usuário pode ativar/desativar notificação por WhatsApp.
  - Prioridade: Média
  - Critérios de Aceite: Estado persistido no banco.

- **RF-03**
  - Descrição: Usuário pode trocar entre tema claro e escuro.
  - Prioridade: Alta
  - Critérios de Aceite: Interface atualiza imediatamente e prefere-se cookie/localStorage.

- **RF-04**
  - Descrição: Configurações são criadas automaticamente ao cadastrar usuário.
  - Prioridade: Alta
  - Critérios de Aceite: Após cadastro, existe instância Configurações_Conta.

## 4. Requisitos Não-Funcionais

- **RNF-01**
  - Categoria: Desempenho
  - Descrição: Carregamento das configurações em ≤ 100 ms.
  - Métrica/Meta: p95 ≤ 100 ms

- **RNF-02**
  - Categoria: Confiabilidade
  - Descrição: Garantia de relação 1:1 sem duplicatas.
  - Métrica/Meta: 0 falhas em testes de unicidade.

## 5. Casos de Uso

### UC-01 – Configurar Notificações por Email
1. Usuário acessa página de configurações.  
2. Marca/desmarca a opção “Receber notificações por email”.  
3. Clica em “Salvar”.  
4. Sistema persiste preferência e exibe confirmação.

### UC-02 – Configurar Notificações por WhatsApp
1. Usuário seleciona “Receber notificações por WhatsApp”.  
2. Salva alterações.  
3. Sistema persiste e exibe aviso de confirmação.

### UC-03 – Alternar Tema
1. Usuário clica no toggle de tema.  
2. Interface muda para tema escuro/claro.  
3. Configuração é salva para próximas sessões.

## 6. Regras de Negócio
- Cada usuário deve possuir exatamente uma instância de Configurações_Conta.  
- Instância criada automaticamente após registro.  
- Preferências independentes de permissões.

## 7. Modelo de Dados

- **ConfiguracoesConta**  
  - user: OneToOneField(User, on_delete=CASCADE, related_name='configuracoes')  
  - receber_notificacoes_email: BooleanField(default=True)  
  - receber_notificacoes_whatsapp: BooleanField(default=False)  
  - tema_escuro: BooleanField(default=False)  
  - created_at: datetime  
  - updated_at: datetime  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Configurações de Conta
  Scenario: Usuário altera preferências de email
    Given usuário autenticado
    When altera "receber_notificacoes_email" para false
    Then configuração é salva e estado permanece false

  Scenario: Instância criada no cadastro
    Given novo usuário registrado
    When conta criada
    Then existe ConfiguracoesConta vinculada ao usuário
```

## 9. Dependências / Integrações
- **App Accounts**: cria instância inicial de configurações.  
- **Redis**: armazenamento de sessão opcional.  
- **Celery**: dispara e-mails de notificação conforme preferências.  
- **Front-end**: localStorage para tema (fallback).

## 10. Anexos e Referências
- Documento fonte: Requisitos_Configuracoes_Conta_Hubx.pdf


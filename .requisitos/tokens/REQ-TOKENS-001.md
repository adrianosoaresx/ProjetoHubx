---
id: REQ-TOKENS-001
title: Requisitos Tokens Hubx
module: Tokens
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source: Requisitos_Tokens_Hubx.pdf
---

## 1. Visão Geral

O App Tokens gerencia a criação, validação e expiração de tokens de acesso para diferentes perfis de usuário (admin, associado, nucleado, coordenador e convidado), assegurando segurança e rastreabilidade no Hubx.

## 2. Escopo
- **Inclui**:
  - Geração de tokens únicos para acesso a funcionalidades específicas.
  - Validação e expiração automática de tokens.
  - Associação de tokens a usuário, organização e núcleos.
  - Registro de uso e mudança de estado de tokens.
- **Exclui**:
  - Autenticação completa (delegado ao App Accounts).
  - Log de sessões e devices.

## 3. Requisitos Funcionais

- **RF‑01**
  - Descrição: Gerar token único e seguro (UUID4 ou `secrets.token_urlsafe`).
  - Prioridade: Alta
  - Critérios de Aceite: Token gerado com `codigo` único; HTTP 201 retorna token.

- **RF‑02**
  - Descrição: Validar token em endpoint de uso.
  - Prioridade: Alta
  - Critérios de Aceite: `GET /api/tokens/validate/?codigo=<código>` retorna estado e dados associados.

- **RF‑03**
  - Descrição: Expirar token após `data_expiracao`.
  - Prioridade: Média
  - Critérios de Aceite: Estado muda de `novo` para `expirado`; uso após expiração retorna erro 400.

- **RF‑04**
  - Descrição: Marcar token como `usado` no primeiro uso válido.
  - Prioridade: Alta
  - Critérios de Aceite: Após uso, `estado='usado'`; reuso retorna erro 409.

- **RF‑05**
  - Descrição: Restringir geração de tokens conforme perfil de quem gera.
  - Prioridade: Alta
  - Critérios de Aceite: Regras de permissão aplicadas (root→admin, admin→associado/nucleado/coordenador, coordenador→convidado).

## 4. Requisitos Não‑Funcionais

- **RNF‑01**
  - Categoria: Segurança
  - Descrição: Tokens criptograficamente seguros e imprevisíveis.
  - Métrica/Meta: Entropia mínima de 128 bits.

- **RNF‑02**
  - Categoria: Desempenho
  - Descrição: Validação de token em p95 ≤ 100 ms.
  - Métrica/Meta: 100 ms

- **RNF‑03**
  - Categoria: Rastreabilidade
  - Descrição: Log de uso de tokens para auditoria.
  - Métrica/Meta: 100% dos eventos registrados.

## 5. Casos de Uso

### UC‑01 – Gerar Token
1. Usuário autenticado com permissão apropriada solicita criação de token.  
2. Sistema valida perfil e gera token.  
3. Retorna HTTP 201 com `codigo`, `tipo_destino` e `data_expiracao`.

### UC‑02 – Validar Token
1. Cliente envia token para endpoint de validação.  
2. Sistema verifica `estado` e `data_expiracao`.  
3. Retorna dados do token ou erro apropriado.

### UC‑03 – Usar Token
1. Cliente usa token em ação de autorização.  
2. Sistema marca `estado='usado'` e associa `usuario`/`nucleo`.  
3. Próximas requisições com mesmo token são rejeitadas.

### UC‑04 – Expirar Token
1. Scheduler ou validação em uso detecta `data_expiracao < agora`.  
2. Sistema atualiza `estado='expirado'`.

## 6. Regras de Negócio
- Token pode ser usado apenas se `estado='novo'` e `data_expiracao > agora`.  
- Após uso válido, `estado` muda para `usado`.  
- Associação automática de `usuario`, `organizacao` e `nucleos` conforme `tipo_destino`.  
- Perfis sem permissão para geração devem receber erro 403.

## 7. Modelo de Dados

- **TokenAcesso**  
  - codigo: string (PK, unique, não editável)  
  - tipo_destino: enum('admin','associado','nucleado','coordenador','convidado')  
  - estado: enum('novo','usado','expirado')  
  - data_expiracao: datetime  
  - gerado_por: FK → User.id  
  - usuario: FK → User.id (opcional)  
  - organizacao: FK → Organizacao.id  
  - nucleos: M2M → Nucleo.id (opcional)  
  - created_at, updated_at: datetime  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Gerenciamento de Tokens
  Scenario: Gerar token para associado
    Given usuário admin autenticado
    When solicita POST /api/tokens/ com tipo_destino=associado
    Then token é criado e retorna HTTP 201

  Scenario: Reusar token usado
    Given token com estado 'usado'
    When tenta validar novamente
    Then retorna HTTP 409 Conflict
```

## 9. Dependências / Integrações
- **App Accounts**: validação de `gerado_por` e `usuario`.  
- **App Organizações/Núcleos**: validação de escopo.  
- **Scheduler**: expiração automática de tokens.  
- **Redis**: cache temporário de tokens para alta performance.  
- **Sentry**: log de erros em geração/validação.

## 10. Anexos e Referências
- Documento fonte: Requisitos_Tokens_Hubx.pdf

## 11. Melhorias e Extensões (Auditoria 2025‑07‑25)

### Requisitos Funcionais Adicionais
- **RF‑06** – Limitar a geração de tokens a no máximo 5 por usuário por dia. Requisições acima deste limite retornam erro 429.  
- **RF‑07** – Registrar metadados de geração e uso de tokens (IP de origem, user agent).  
- **RF‑08** – Permitir revogação manual de tokens, alterando estado para `revogado`.  

### Requisitos Não‑Funcionais Adicionais
- **RNF‑04** – Logs de uso e revogação devem ser criptografados e retidos por 1 ano para auditoria.  

### Modelo de Dados Adicional
- `TokenAcesso`: adicionar `ip_gerado: string`, `ip_utilizado: string`, `revogado_em: datetime`, `revogado_por: FK → User.id`.  
- Criar tabela `TokenUsoLog` com campos: id, token_codigo, usuario_id, acao (`geracao`,`validacao`,`uso`,`revogacao`), ip, timestamp.  

### Regras de Negócio Adicionais
- Requisições de geração acima de 5 tokens/dia devem ser bloqueadas.  
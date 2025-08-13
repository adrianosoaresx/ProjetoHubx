---
id: REQ-TOKENS-001
title: Requisitos Tokens Hubx
module: Tokens
status: Em vigor
version: '1.1'
updated: '2025-08-13'
---

## 1. Visão Geral
O app Tokens fornece mecanismos de credencial temporária e permanente no Hubx. Abrange convites com uso único, tokens de API com escopos, códigos de autenticação e dispositivos TOTP. Cada emissão e uso é registrado para auditoria.

## 2. Escopo
- Inclui: geração, validação, uso e revogação de tokens de convite; gerenciamento de tokens de API; emissão e verificação de códigos de autenticação e TOTP; logs e tarefas de limpeza.
- Exclui: autenticação completa (delegada ao app Accounts); políticas de sessão; armazenamento de segredos fora do banco.

## 3. Requisitos Funcionais
- **RF-01** Gerar token de convite único e seguro; retorno HTTP 201 com código e dados.
- **RF-02** Validar token de convite via `GET /api/tokens/validate/?codigo=` indicando estado e dados.
- **RF-03** Expirar token após `data_expiracao` e bloquear uso posterior.
- **RF-04** Marcar token de convite como usado no primeiro uso válido; tentativas seguintes retornam 409.
- **RF-05** Restringir geração de convites por perfil (root→admin, admin→demais, gestor→convidado).
- **RF-06** Limitar emissão a cinco convites por usuário por dia; excesso retorna 429.
- **RF-07** Registrar IP e user agent na geração, validação, uso e revogação.
- **RF-08** Permitir revogação manual de convites, alterando estado para `revogado`.
- **RF-09** Gerar token de API com escopo (`read`, `write`, `admin`), cliente opcional e expiração.
- **RF-10** Listar e revogar tokens de API do usuário; admins podem gerir todos.
- **RF-11** Autenticar requisições via header `Authorization: Bearer <token>` validando expiração e revogação.
- **RF-12** Gerar códigos de autenticação de seis dígitos com validade de 10 minutos e registrar tentativas.
- **RF-13** Registrar dispositivo TOTP para 2FA e gerar códigos temporários.
- **RF-14** Disponibilizar auditoria completa dos tokens de convite via `GET /api/tokens/<id>/logs/`.
- **RF-15** (Futuro) Permitir rotação automática de tokens de API, emitindo novo par e revogando o antigo.
- **RF-16** (Futuro) Vincular tokens a fingerprint de device opcional.
- **RF-17** (Futuro) Suportar listas de IP allow/deny por token.
- **RF-18** (Futuro) Aplicar rate limit por token/usuário/IP com políticas de burst e sustained.
- **RF-19** (Futuro) Emitir webhooks de ciclo de vida (emissão, uso, revogação) com assinatura HMAC e reentrega com backoff.

## 4. Requisitos Não Funcionais
- **RNF-01** Segurança: tokens devem ter entropia ≥128 bits e nunca serem logados em texto claro.
- **RNF-02** Desempenho: validação de token deve manter p95 ≤200 ms.
- **RNF-03** Rastreabilidade: 100% dos eventos registrados em TokenUsoLog ou campo equivalente.
- **RNF-04** Modelos do app devem herdar de `TimeStampedModel` e implementar `SoftDeleteModel` quando exclusão lógica for necessária.
- **RNF-05** Logs de uso e revogação criptografados e retidos por 1 ano; limpeza automática diária.
- **RNF-06** Métricas Prometheus para tokens emitidos, revogados, falhas de validação e latência.
- **RNF-07** Armazenamento de códigos e segredos em repouso com criptografia ou hashing adequado.
- **RNF-08** Política de rollback: revogações devem ser idempotentes e registradas com `revogado_por` e `revogado_em`.

## 5. Casos de Uso
- Gerar token de convite para associado.
- Validar token de convite recebido por e-mail.
- Usar token para ativar conta e marcar como usado.
- Revogar token comprometido por administrador.
- Gerar token de API para integração externa.
- Autenticar requisição usando token de API.

## 6. Regras de Negócio
- Token só pode ser usado se `estado='novo'` e `data_expiracao` futura.
- Após uso ou revogação, token não pode ser reutilizado.
- Usuário que exceder cinco convites diários é bloqueado até o próximo dia.
- Escopo `admin` só é permitido a superusers.

## 7. Modelo de Dados
- **ApiToken**: id UUID, user (FK), client_name, token_hash, scope, expires_at, revoked_at, last_used_at.
- **TokenAcesso**: codigo, tipo_destino, estado, data_expiracao, ip_gerado, ip_utilizado, revogado_em, revogado_por (FK), gerado_por (FK), usuario (FK), organizacao (FK), nucleos (M2M).
- **TokenUsoLog**: id UUID, token (FK), usuario (FK opcional), acao, ip criptografado, user_agent criptografado, timestamp.
- **CodigoAutenticacao**: usuario (FK), codigo, expira_em, verificado, tentativas.
- **TOTPDevice**: usuario (OneToOne), secret, confirmado.

## 8. Dependências e Integrações
- Accounts para validação de usuários e eventos de segurança.
- Celery para tarefas de limpeza e revogação automática.
- Redis opcional para cache de tokens intensamente lidos.
- Sentry para captura de erros.
- Prometheus para métricas.

## 9. Requisitos Adicionais / Melhorias
- Implementar device binding, IP allow/deny e rate limiting conforme RF-16 a RF-18.
- Expor métricas e webhooks conforme RNF-06 e RF-19.

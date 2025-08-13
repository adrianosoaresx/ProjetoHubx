### Visão geral
O app Tokens gerencia diferentes credenciais de uso no Hubx. Ele emite códigos de acesso temporários para convites, gera tokens de API com escopos e expiração, registra auditoria de geração e uso e oferece suporte a códigos de autenticação e dispositivos TOTP para 2FA.

### Funcionalidades faltantes em relação ao requisito
- Restrição de geração de tokens conforme perfil de quem gera; hoje qualquer usuário autenticado pode emitir convites.
- Garantia de validação em p95 ≤ 100 ms; não há métricas de latência.
- Herança de TimeStampedModel para todos os modelos; TokenUsoLog não herda.
- Suporte a exclusão lógica (SoftDeleteModel) para modelos de token e logs.

### Funcionalidades extras encontradas
- Emissão de tokens de API com escopos "read", "write" e "admin", expiração e revogação manual.
- Limite diário de cinco convites por usuário.
- Registro criptografado de IP e user agent em TokenUsoLog.
- Tarefas Celery para remover logs com mais de um ano e revogar tokens de API expirados.
- Recursos de 2FA: códigos de autenticação temporários e dispositivos TOTP.

### Divergências de contratos de API
- Requisitos não mencionam endpoints para tokens de API (`/api/api-tokens/`).
- Não há especificação formal para retorno de erros padronizados; respostas variam entre 400, 403, 409 e 429.

### Requisitos não funcionais atendidos vs pendentes
- Segurança: tokens e metadados gerados com fontes seguras e campos sensíveis criptografados.
- Desempenho: ausência de métricas impede comprovação de p95 ≤ 100 ms.
- Observabilidade: logs de auditoria existem, mas faltam métricas Prometheus e webhooks de ciclo de vida.
- Auditoria: registros completos de geração, validação, uso e revogação.

### Riscos técnicos e débito tecnológico
- Códigos de convite armazenados em texto claro; exposição do banco compromete tokens ativos.
- Ausência de rate limit por token, device binding e controle de IP permite abuso.
- Falta de métricas e monitoramento dificulta detecção de anomalias.
- Modelos sem SoftDelete dificultam recuperação ou análise histórica.

### Recomendações e próximos passos
1. Implementar checagem de permissão por perfil na emissão de convites.
2. Adicionar rate limit por token/usuário/IP e políticas de rotação automática.
3. Introduzir device binding e listas de IP allow/deny opcionais.
4. Medir latência dos endpoints e expor métricas Prometheus.
5. Hash de códigos de convite ou uso de storage seguro para reduzir risco de vazamento.
6. Implementar SoftDeleteModel para tokens e logs e prever webhooks de eventos.

### Checklist de conformidade
- Tipos de token e escopos documentados e validados? Parcial: escopos existem para tokens de API, mas convites não têm escopos nem validação por permission class.
- Expiração/TTL e rotação implementadas? Convites e tokens de API expiram; não há rotação automática nem refresh.
- Revogação/blacklist persistente? Sim, estado `revogado` e `revoked_at` persistem e são checados em cada requisição.
- Rate limit por token/usuário/IP? Apenas limite diário de emissão; não há rate limit de uso.
- Device binding e IP allow/deny opcionais? Ausentes.
- Auditoria de emissão/uso/revogação com correlação? Sim, TokenUsoLog armazena token_id, usuário, IP e user agent.
- Criptografia de segredos em repouso e redaction em logs? Metadados criptografados; códigos de convite em texto claro.
- Métricas de tokens emitidos/revogados/latência? Não existem.
- Testes automatizados dos fluxos críticos (≥90%)? Testes cobrem 31 cenários, mas cobertura global não foi aferida.
- P95 dos endpoints ≤200 ms e caching? Não medido; sem cache dedicado.

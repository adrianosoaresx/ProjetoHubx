# AUDIT-TOKENS-001.md
Auditoria de requisitos – app TOKENS  
Data: 2025-08-18  

## 1. Rastreabilidade Requisito × Implementação

| Requisito | Status | Evidências |
|-----------|--------|-----------|
| RF-01 a RF-14 | Atendido | Vide `tokens/api.py` e `tokens/models.py` |
| RF-15–RF-17 | Não implementado (planejado) | — |
| RF-18 | Parcial (rate limit básico) | `tokens/ratelimit.py` |
| RF-19–RF-20 | Não implementado (webhooks); métricas parciais | — |
| RNF-01 | Atendido | `tokens/services.py` |
| RNF-02 | Risco – busca linear | `tokens/services.py` |
| RNF-03–RNF-05 | Atendido | `tokens/api.py`, `tokens/tasks.py` |
| RNF-06 | Parcial – métricas só para convites | `tokens/metrics.py` |
| RNF-07 | Não atendido – armazenamento em texto claro | `tokens/models.py` |
| RNF-08 | Parcial – convites ok, API tokens sem `revogado_por` | `tokens/models.py` |

## 2. Principais Lacunas
1. Códigos de autenticação e segredos TOTP sem criptografia.
2. Revogação de API tokens sem registro de responsável e não idempotente.
3. Logs de IP/user agent ausentes para API tokens.
4. Webhooks de ciclo de vida e métricas completas faltantes.
5. Busca de tokens por código ineficiente.

## 3. Plano de Sprints
- **Sprint 1 (segurança & logs)**
  - Hash/criptografia de códigos e segredos.
  - Revogação idempotente com `revogado_por`.
  - Registro de IP/user agent para API tokens.

- **Sprint 2 (escalabilidade & observabilidade)**
  - Otimizar `find_token_by_code`.
  - Implementar webhooks e expandir métricas de API tokens.

## 4. Recomendações
Priorizar Sprint 1 para mitigar riscos de segurança e conformidade; Sprint 2 foca escalabilidade e monitoramento.

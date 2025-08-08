# Fluxo de Auditoria

```mermaid
flowchart TD
    R[Requisição] --> M[AuditMiddleware]
    M --> L[AuditLog]
    L --> T[Celery cleanup_old_logs]
```

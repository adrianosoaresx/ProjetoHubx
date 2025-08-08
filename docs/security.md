# Security Overview

This document summarizes how ProjetoHubx addresses common security concerns and the OWASP Top 10 list.

## OWASP Top 10 Checklist

| Item | Mitigation |
| --- | --- |
| Injection | ORM usage and parameterized queries reduce risk of SQL injection. |
| Broken Authentication | Django auth system with hashed passwords and session management. |
| Sensitive Data Exposure | HTTPS recommended, secrets stored in environment variables. |
| XML External Entities (XXE) | No user-supplied XML parsing enabled. |
| Broken Access Control | Permissions enforced via Django permissions and tests. |
| Security Misconfiguration | Default security settings applied and reviewed. |
| Cross-Site Scripting (XSS) | Templates auto-escape; user input sanitized. |
| Insecure Deserialization | No untrusted deserialization in codebase. |
| Using Components with Known Vulnerabilities | `pip-audit` and `safety` used to check dependencies. |
| Insufficient Logging & Monitoring | Prometheus metrics and structured logging via `structlog`. |

Additional security reviews should be performed regularly.

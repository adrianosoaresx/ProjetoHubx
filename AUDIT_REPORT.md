# Audit Report for ProjetoHubx

This document summarizes issues found while auditing the repository for legacy code and compliance with project requirements.

## Environment

Attempts to use the GitHub connector and PDF parsing service failed because the services were unreachable (`localhost:8674` and `localhost:8451`). All searches and PDF extraction were performed locally using `grep` and `pdfminer.six`.

## Legacy Code Patterns

The following patterns were searched: `UserType.objects`, `TipoUsuario`, `tipo_id`, `data_hora`, `duracao`, `link_inscricao`, `inscritos`, `Mensagem(`, `Notificacao(`, `Topico(`, `Resposta(`, `Post.PUBLICO`.

Results:

- **UserType.objects** – occurrences in tests creating a legacy `UserType` model instance:
  - `accounts/tests.py` lines 177–204.
  - `empresas/test_empresas.py` lines 11–15.
- No occurrences of other patterns were found outside fixture data and documentation.

## Model Verification Against PDFs

### Accounts

`User` model contains most fields required by the PDF, including `nome_completo`, `biografia`, `cover`, `fone`, and `whatsapp`.
However, the PDF specifies a JSONField `redes_sociais`, which is missing.

### Configurações de Conta

`ConfiguracaoConta` model includes `receber_notificacoes_email`, `receber_notificacoes_whatsapp`, and `tema_escuro` as required.

### Chat

`ChatMessage` model defines the `organizacao` field as required by the chat specification.

### Dashboard

`DashboardService` implements growth calculations using `get_period_range` and `calcular_crescimento` supporting monthly, trimestral, semestral and annual periods.

## Tests and Scripts

Some tests reference the legacy `UserType` model and `tipo` field. These need updating to the current `user_type` enum:

- `accounts/tests.py` lines 177–204
- `empresas/test_empresas.py` lines 11–15

Management commands and scripts rely on the `UserType` enum and appear up to date.

## Recommended Actions

- Refactor tests to remove creation of `UserType` model instances and update field names to `user_type`.
- Add `redes_sociais` JSONField to `accounts.models.User` if still required, or update documentation to match implementation.
- Ensure `ConfiguracaoConta` and `ChatMessage` maintain the fields as per requirements.
- Verify dashboard views use `DashboardService` metrics consistently.


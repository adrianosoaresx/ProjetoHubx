# Levantamento de risco: `EncryptedCharField` com limites curtos

## Contexto
`EncryptedCharField` usa Fernet, e o valor persistido em banco é sempre maior que o plaintext devido a IV, timestamp, assinatura HMAC e codificação URL-safe Base64. Por isso, `max_length` deve ser calculado para o ciphertext e não para o dado original.

## Inventário de usos com limites curtos (histórico e atual)

| Local | Campo | Limite observado | Tipo de dado | Risco | Ação para PostgreSQL |
|---|---|---:|---|---|---|
| `tokens` | `TokenAcesso.ip_gerado` | 128 (histórico), **255 (atual)** | IPv4/IPv6 | **Alto** quando 128 (IPv6 + Fernet pode exceder) | Migração de aumento para 255 concluída em `tokens/migrations/0022_alter_codigoautenticacaolog_ip_and_more.py`. |
| `tokens` | `TokenAcesso.ip_utilizado` | 128 (histórico), **255 (atual)** | IPv4/IPv6 | **Alto** quando 128 | Migração de aumento para 255 concluída em `tokens/migrations/0022_alter_codigoautenticacaolog_ip_and_more.py`. |
| `tokens` | `TokenUsoLog.ip` | 128 (histórico), **255 (atual)** | IPv4/IPv6 | **Alto** quando 128 | Migração de aumento para 255 concluída em `tokens/migrations/0022_alter_codigoautenticacaolog_ip_and_more.py`. |
| `tokens` | `CodigoAutenticacaoLog.ip` | 128 (histórico), **255 (atual)** | IPv4/IPv6 | **Alto** quando 128 | Migração de aumento para 255 concluída em `tokens/migrations/0022_alter_codigoautenticacaolog_ip_and_more.py`. |
| `accounts` | `User.two_factor_secret` | 128 (histórico), 512 (intermediário), **TextField (atual)** | segredo TOTP/Base32 | **Alto** em limites fixos curtos e **Médio** com crescimento futuro | Migração para `EncryptedTextField` concluída em `accounts/migrations/0028_alter_user_two_factor_secret.py`. |
| `tokens` | `TOTPDevice.secret` | 128 (histórico), 512 (intermediário), **TextField (atual)** | segredo TOTP/Base32 | **Alto** em 128; **Médio** em 512 para cenários atípicos | Migração para `EncryptedTextField` concluída em `tokens/migrations/0022_alter_codigoautenticacaolog_ip_and_more.py`. |

> Observação: não foram encontrados usos atuais com `max_length=150` para `EncryptedCharField`; os limites curtos relevantes no código/migrations foram principalmente 45 e 128.

## Plano de migrations (PostgreSQL)
1. **Aumentar colunas de IP de 128 para 255** em `tokens` (feito):
   - `tokenacesso.ip_gerado`
   - `tokenacesso.ip_utilizado`
   - `tokenusolog.ip`
   - `codigoautenticacaolog.ip`
2. **Migrar segredos de tamanho imprevisível para `EncryptedTextField`** (feito):
   - `accounts_user.two_factor_secret`
   - `tokens_totpdevice.secret`
3. **Rodar validação pós-migração**:
   - smoke test de criação/leitura de segredos TOTP longos (incluído em teste automatizado).
   - monitorar erros de `value too long for type character varying` no Sentry/observabilidade por 7 dias.

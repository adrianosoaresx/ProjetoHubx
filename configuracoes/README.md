# Configurações de Conta

Este aplicativo centraliza as preferências de cada usuário através do modelo
`ConfiguracaoConta`. Cada usuário possui exatamente uma instância, criada
automaticamente após o cadastro.

## Campos principais

- `receber_notificacoes_email` e `frequencia_notificacoes_email`
- `receber_notificacoes_whatsapp` e `frequencia_notificacoes_whatsapp`
- `idioma`
- `tema`

## Atualização via serviço

Use `atualizar_preferencias_usuario(usuario, dados)` para aplicar mudanças de
forma segura e invalidar o cache.

### Exemplo

```python
from configuracoes.services import atualizar_preferencias_usuario

atualizar_preferencias_usuario(
    request.user,
    {"tema": "escuro", "idioma": "en-US"},
)
```

As preferências são expostas na interface na aba **Preferências** dentro de
`/configuracoes/` e também pela API em `configuracoes/api/`.

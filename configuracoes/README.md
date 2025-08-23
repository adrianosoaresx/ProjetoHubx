# Configurações de Conta

Este aplicativo centraliza as preferências de cada usuário através do modelo
`ConfiguracaoConta`. Cada usuário possui exatamente uma instância, criada
automaticamente após o cadastro. O modelo herda de
`core.models.TimeStampedModel`, fornecendo os campos `created_at` e
`updated_at`, e de `core.models.SoftDeleteModel`, que adiciona `deleted` e
`deleted_at` para exclusão lógica.

## Campos principais

- `receber_notificacoes_email` e `frequencia_notificacoes_email`
- `receber_notificacoes_whatsapp` e `frequencia_notificacoes_whatsapp`
- `idioma`
- `tema`
- `hora_notificacao_diaria`, `hora_notificacao_semanal` e `dia_semana_notificacao`

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
Para consultar registros removidos logicamente utilize o manager
`ConfiguracaoConta.all_objects`.

### API

```
GET /configuracoes/api/
```

Resposta:

```json
{
  "receber_notificacoes_email": true,
  "frequencia_notificacoes_email": "imediata",
  "receber_notificacoes_whatsapp": false,
  "frequencia_notificacoes_whatsapp": "diaria",
  "idioma": "pt-BR",
  "tema": "claro",
  "hora_notificacao_diaria": "08:00:00",
  "hora_notificacao_semanal": "08:00:00",
  "dia_semana_notificacao": 0
}
```

Use `PATCH /configuracoes/api/` para atualizar campos específicos. Consulte a
documentação OpenAPI gerada para exemplos completos.

## Cookies

Ao salvar as preferências pelo formulário, o sistema envia os cookies
`tema` e `django_language` com `SameSite=Lax`. O atributo `secure` é
ativado automaticamente em conexões HTTPS e `HttpOnly` permanece
desabilitado para permitir acesso via JavaScript.

## Fixtures de exemplo

Para demonstrar diferentes combinações de preferências é possível carregar os
dados de `configuracoes/fixtures/configuracoes_exemplo.json`:

```bash
python manage.py loaddata configuracoes/fixtures/configuracoes_exemplo.json
```

Isso criará alguns registros de `ConfiguracaoConta` com valores variados para
testes e desenvolvimento.

## Testes e traduções

Para executar a suíte de testes deste app:

```bash
pytest tests/configuracoes -q
```

Para gerar e compilar as traduções (inglês e espanhol):

```bash
python manage.py makemessages -l en -l es
python manage.py compilemessages
```

## Frontend

A lógica de alternância de campos e atualização de idioma/tema da aba
**Preferências** está localizada em `static/configuracoes/preferencias.js` e é
incluída nos templates via tag `{% static %}`.

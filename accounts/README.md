# Accounts App

Todos os modelos deste app herdam de `TimeStampedModel` para os campos `created_at` e `updated_at` e utilizam `SoftDeleteModel` para exclusão lógica através dos campos `deleted` e `deleted_at`.

Para criar um novo modelo:

```python
from core.models import TimeStampedModel, SoftDeleteModel

class Exemplo(TimeStampedModel, SoftDeleteModel):
    ...
```

A exclusão padrão é lógica, basta chamar `instance.delete()`. Para remover definitivamente, use `instance.delete(soft=False)`.
Para o modelo `User`, ao excluir definitivamente (`soft=False`), os arquivos `avatar` e `cover`
associados ao usuário também são removidos do armazenamento.

## Fluxo de registro

O cadastro de novos usuários ocorre exclusivamente pelo fluxo multietapas
iniciado em `/accounts/onboarding/`. Detalhes de cada etapa estão descritos na
[documentação de registro multietapas](../docs/accounts/registro_multietapas.md).

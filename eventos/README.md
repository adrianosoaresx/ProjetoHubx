# Eventos

Este app substitui o antigo módulo **Agenda**, mantendo o label `agenda`
para compatibilidade com migrations e chaves estrangeiras existentes.

Todos os modelos deste app herdam de `core.models.TimeStampedModel`,
disponibilizando os campos `created_at` e `updated_at` para registro de
criação e atualização.

Os modelos `Evento` e `InscricaoEvento` também utilizam
`core.models.SoftDeleteModel` com o manager `SoftDeleteManager`,
possibilitando exclusão lógica através dos campos `deleted` e
`deleted_at`.

Para remover um registro definitivamente utilize `obj.delete(soft=False)`.

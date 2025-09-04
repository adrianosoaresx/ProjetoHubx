# Eventos

Documentação do app de eventos, sucessor do módulo **Agenda**.

Todos os modelos herdam de `core.models.TimeStampedModel`, com os campos
`created_at` e `updated_at` para registrar criação e atualização.

Os modelos `Evento` e `InscricaoEvento` também utilizam
`core.models.SoftDeleteModel` e o manager `SoftDeleteManager` para exclusão
lógica via `deleted` e `deleted_at`.

Para remover um registro definitivamente utilize `obj.delete(soft=False)`.

# Organizações

Este app gerencia as organizações cadastradas na plataforma. Implementa CRUD completo com busca avançada, associações e histórico de alterações seguindo a arquitetura limpa.

Todas as entidades utilizam os mixins `TimeStampedModel` e `SoftDeleteModel`, garantindo campos padronizados de criação/atualização (`created_at`, `updated_at`) e exclusão lógica (`deleted`, `deleted_at`).

## Funcionalidades principais

- **Listagem e busca**: campo único que aceita nome ou *slug*. Resultados paginados (10 por página) e filtrados para ocultar itens excluídos ou inativos.
- **Criação e edição**: formulário inclui avatar e capa. O usuário autenticado é registrado como `created_by`. Slug é normalizado e validado para garantir unicidade.
- **Exclusão lógica**: remover uma organização marca `deleted=True` e registra `deleted_at`; nenhuma linha é removida do banco.
- **Inativar/Reativar**: superadmin pode alternar o status `inativa`. A ação é registrada com `OrganizacaoAtividadeLog`.
- **Associações**: página de detalhes mostra usuários, núcleos, eventos, empresas e posts relacionados, com contadores e links rápidos.
- **Logs e notificações**: alterações relevantes geram `OrganizacaoChangeLog` e ações geram `OrganizacaoAtividadeLog`; ambas disparam o sinal `organizacao_alterada` que notifica os membros.

## Sinal `organizacao_alterada`

Exemplo de uso:

```python
from organizacoes.tasks import organizacao_alterada

organizacao_alterada.send(
    sender=__name__,
    organizacao=org,
    acao="updated",
)
```

O *payload* é consumido por `enviar_email_membros`, que encaminha mensagens aos usuários associados.

## Histórico

A lista de alterações pode ser consultada em `/organizacoes/<id>/historico/` (apenas admins da organização ou superusuários). Os registros de log são imutáveis e preservam os dados relevantes de cada ação.

## Recursos associados

Endpoints para gerenciar recursos vinculados à organização. Apenas usuários com permissões administrativas da organização podem utilizar estas rotas.

- **Listar**: `GET /api/organizacoes/<organizacao_id>/recursos/`
- **Criar**: `POST /api/organizacoes/<organizacao_id>/recursos/`
- **Remover**: `DELETE /api/organizacoes/<organizacao_id>/recursos/<id>/`

O corpo do `POST` deve conter `content_type` e `object_id` do recurso a ser associado (por exemplo, um projeto ou evento).

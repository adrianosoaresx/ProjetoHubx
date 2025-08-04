# Organizações

Este app gerencia as organizações cadastradas na plataforma. Implementa CRUD completo com busca avançada, associações e histórico de alterações seguindo a arquitetura limpa.

Todas as entidades utilizam os mixins `TimeStampedModel` e `SoftDeleteModel`, garantindo campos padronizados de criação/atualização (`created_at`, `updated_at`) e exclusão lógica (`deleted`, `deleted_at`).

## Funcionalidades principais

- **Listagem e busca**: campo único que aceita nome ou *slug*. Resultados paginados (10 por página) e filtrados para ocultar itens excluídos ou inativos.
- **Criação e edição**: formulário inclui avatar e capa. O usuário autenticado é registrado como `created_by`. Slug é normalizado e validado para garantir unicidade.
- **Exclusão lógica**: remover uma organização marca `deleted=True` e registra `deleted_at`; nenhuma linha é removida do banco.
- **Inativar/Reativar**: superadmin pode alternar o status `inativa`. A ação é registrada com `OrganizacaoLog`.
- **Associações**: página de detalhes mostra usuários, núcleos, eventos, empresas e posts relacionados, com contadores e links rápidos.
- **Logs e notificações**: todas as alterações geram entradas em `OrganizacaoLog` e disparam o sinal `organizacao_alterada` que notifica os membros.

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

A lista de alterações pode ser consultada em `/organizacoes/<id>/logs/` (somente superadmin). Os registros de `OrganizacaoLog` são imutáveis e preservam os dados anteriores e novos de cada ação.

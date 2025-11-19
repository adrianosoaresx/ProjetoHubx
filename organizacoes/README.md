# Organizações

Este app gerencia as organizações cadastradas na plataforma. Implementa CRUD completo com busca avançada, associações e histórico de alterações seguindo a arquitetura limpa.

Todas as entidades utilizam os mixins `TimeStampedModel` e `SoftDeleteModel`, garantindo campos padronizados de criação/atualização (`created_at`, `updated_at`) e exclusão lógica (`deleted`, `deleted_at`).

## Funcionalidades principais

- **Listagem e busca**: campo único que aceita nome. Resultados paginados (10 por página) e filtrados para ocultar itens excluídos ou inativos.
- **Criação e edição**: formulário inclui avatar e capa. O usuário autenticado é registrado como `created_by`. Slug é normalizado e validado para garantir unicidade.
- **Exclusão lógica**: remover uma organização marca `deleted=True` e registra `deleted_at`; nenhuma linha é removida do banco.
- **Inativar/Reativar**: superadmin pode alternar o status `inativa`. A ação é registrada com `OrganizacaoAtividadeLog`.
- **Associações**: página de detalhes mostra usuários, núcleos, eventos, empresas e posts relacionados, com contadores e links rápidos.
- **Logs e notificações**: alterações relevantes geram `OrganizacaoChangeLog` e ações geram `OrganizacaoAtividadeLog`; ambas disparam o sinal `organizacao_alterada` que notifica os membros.

## Publicação automática de feeds de notícias

- **Configuração**: cada organização pode informar uma URL RSS/Atom no campo
  `feed_noticias`. A página `/organizacoes/<id>/` exibe o endereço configurado
  para consulta rápida.
- **Agendamento**: a tarefa Celery `publicar_feed_noticias_task` roda
  diariamente às 04:00 (`CELERY_BEAT_SCHEDULE["publicar_feed_noticias_diario"]`)
  e processa apenas organizações ativas com `feed_noticias` definido. Um lock em
  cache evita execuções concorrentes por 10 minutos.
- **Autor e tags**: os posts são publicados em nome do primeiro administrador
  ativo da organização (ou criador/membro mais antigo) e marcados com a tag
  `"notícias"`. O limite padrão é de 3 itens por organização e execução
  (`max_items`). O `tipo_feed` padrão é `global`.
- **Observabilidade**: logs trazem `organizacao` e `external_id`, e as criações
  incrementam o counter Prometheus `feed_posts_created_total`. Exceções são
  reportadas ao Sentry; recomenda-se alertas para falhas repetidas ou ausência
  de novos posts em execuções consecutivas.
- **Execução inicial**: após um deploy, execute manualmente a função
  `publicar_feed_noticias` para preencher o histórico se necessário:

  ```bash
  python manage.py shell -c "from organizacoes.services import publicar_feed_noticias; publicar_feed_noticias()"
  ```

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

O *payload* é consumido por `enviar_email_membros`, que encaminha mensagens aos membros da organização.

## Histórico

A lista de alterações pode ser consultada em `/organizacoes/<id>/historico/` (apenas admins da organização ou superusuários). Os registros de log são imutáveis e preservam os dados relevantes de cada ação.

## Recursos de membros

Endpoints para gerenciar recursos vinculados à organização. Apenas usuários com permissões administrativas da organização podem utilizar estas rotas.

- **Listar**: `GET /api/organizacoes/<organizacao_id>/recursos/`
- **Criar**: `POST /api/organizacoes/<organizacao_id>/recursos/`
- **Remover**: `DELETE /api/organizacoes/<organizacao_id>/recursos/<id>/`

O corpo do `POST` deve conter `content_type` e `object_id` do recurso a ser associado (por exemplo, um projeto ou evento).

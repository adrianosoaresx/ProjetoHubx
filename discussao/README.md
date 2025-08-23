# Módulo Discussão

Este app provê fórum simples com categorias, tópicos e respostas.

## Padrões de modelo

Os modelos deste app herdam de `TimeStampedModel`, que disponibiliza os
campos `created` e `modified`. `CategoriaDiscussao`, `TopicoDiscussao` e
`RespostaDiscussao` também utilizam `core.models.SoftDeleteModel`, permitindo
exclusão lógica através dos campos `deleted` e `deleted_at`.

## Endpoints principais

| Método | Caminho | Descrição |
|--------|--------|-----------|
| GET | `/discussao/` | lista categorias |
| POST | `/discussao/categorias/novo/` | cria categoria (admin) |
| GET/POST | `/discussao/<categoria>/novo/` | cria tópico |
| POST | `/discussao/<categoria>/<topico>/resolver/` | marca tópico como resolvido |
| POST | `/discussao/<categoria>/<topico>/responder/` | cria resposta |
| POST | `/discussao/comentario/<id>/editar/` | edita resposta |
| GET/POST | `/api/discussao/discussao/categorias/` | CRUD de categorias (API) |
| POST | `/api/discussao/discussao/votos/` | votar em tópicos ou respostas |

## Casos de uso

- **UC-01** criar categorias.
- **UC-02** listar tópicos com filtros e busca.
- **UC-03** criar/editar tópicos.
- **UC-04** responder tópicos e editar respostas.
- **UC-05** votar em tópicos e respostas.
- **UC-06** marcar resolução e melhor resposta.
- **UC-07** filtrar por tags e texto.
- **UC-08** acompanhar atualizações em tempo real.
- **UC-09** denunciar conteúdo para moderação.

## Regras de negócio

* Apenas membros da organização podem participar.
* Autor ou administrador podem editar e resolver tópicos/respostas.

## Estratégia de cache

As listagens de categorias e de tópicos utilizam cache de página por 60s.
As chaves são geradas em `cache_utils.py` e invalidadas de forma
seletiva com `cache.delete` sempre que categorias, tópicos ou respostas
relevantes são modificados.

## Moderação

Moderadores podem sinalizar conteúdo impróprio e revisar no `DiscussionModerationLog`.


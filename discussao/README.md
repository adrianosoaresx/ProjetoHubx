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

## Moderação

Moderadores podem sinalizar conteúdo impróprio e revisar no `DiscussionModerationLog`.

## Configuração

- `DISCUSSAO_ALLOWED_EXTS`: extensões permitidas para anexos (`.jpg`, `.jpeg`, `.png`, `.gif`, `.pdf`).
- `DISCUSSAO_ALLOWED_MIME_PREFIXES`: prefixos MIME aceitos (`image/`, `application/pdf`).
- `DISCUSSAO_MAX_FILE_MB`: tamanho máximo dos anexos (padrão 20 MB).
- `FEATURE_DISCUSSAO_AGENDA`: habilita ação opcional de agendar tópicos na Agenda.


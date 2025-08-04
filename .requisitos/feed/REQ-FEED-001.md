---
id: REQ-FEED-001
title: Requisitos Feed Hubx Atualizado
module: Feed
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source: Requisitos_Feed_Hubx_Atualizado.pdf
---

## 1. Visão Geral

O App Feed permite exibir e gerenciar publicações de texto e mídia, organizadas por tipo (global, usuário, núcleo ou evento), oferecendo filtragem, paginação e controle de permissões conforme o escopo associado.

## 2. Escopo
- **Inclui**:  
  - Listagem de posts por tipo_feed e filtros (organização, tags).  
  - Criação, edição e remoção de posts contendo texto, imagem ou PDF.  
  - Upload e download de arquivos associados aos posts.  
  - Paginação e ordenação de publicações.  
- **Exclui**:  
  - Chat em tempo real (delegado ao App Chat).  
  - Integração com serviços de faturamento.

## 3. Requisitos Funcionais

- **RF‑01**  
  - Descrição: Listar posts do feed conforme `tipo_feed` (global, usuário, núcleo, evento).  
  - Prioridade: Alta  
  - Critérios de Aceite: Retorna lista paginada via `GET /api/feed/?tipo_feed=<tipo>&...`.  

- **RF‑02**  
  - Descrição: Criar novo post com texto e mídia (imagem ou PDF).  
  - Prioridade: Alta  
  - Critérios de Aceite: `POST /api/feed/` aceita `conteudo`, `tipo_feed`, `file`; retorna HTTP 201.  

- **RF‑03**  
  - Descrição: Editar post existente pelo autor ou admin.  
  - Prioridade: Média  
  - Critérios de Aceite: `PUT/PATCH /api/feed/<id>/`; atualiza campos permitidos.  

- **RF‑04**  
  - Descrição: Excluir post pelo autor ou admin (soft delete).  
  - Prioridade: Média  
  - Critérios de Aceite: `DELETE /api/feed/<id>/`; marca `deleted=true`.  

- **RF‑05**  
  - Descrição: Filtrar feed por organização, tags e data de criação.  
  - Prioridade: Média  
  - Critérios de Aceite: Parâmetros `?organizacao=<id>&tags=<t1,t2>&date_from=<data>`.  

- **RF‑06**  
  - Descrição: Fazer upload seguro de arquivos, armazenando em S3.  
  - Prioridade: Alta  
  - Critérios de Aceite: URLs de upload/download válidos e protegidos.  

## 4. Requisitos Não‑Funcionais

- **RNF‑01**  
  - Categoria: Desempenho  
  - Descrição: Listagem e paginação com p95 ≤ 300 ms  
  - Métrica/Meta: 300 ms  

- **RNF‑02**  
  - Categoria: Confiabilidade  
  - Descrição: Upload de arquivos resiliente a falhas de rede  
  - Métrica/Meta: Retries automáticos até 3 tentativas  

- **RNF‑03**  
  - Categoria: Segurança  
  - Descrição: Controle de acesso baseado em escopo e permissões  
  - Métrica/Meta: 0 acessos indevidos em testes de penetração  


- **RNF‑04**: Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`), garantindo consistência e evitando campos manuais.
- **RNF‑05**: Quando houver necessidade de exclusão lógica, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando os campos `deleted` e `deleted_at`.

## 5. Casos de Uso

### UC‑01 – Listar Feed
1. Usuário acessa endpoint de listagem com parâmetros de filtro.  
2. Sistema retorna posts paginados.  
3. Interface exibe posts com mídia e metadados.

### UC‑02 – Criar Post
1. Usuário envia `conteudo` e arquivo via formulário.  
2. Backend valida e armazena mídia em S3.  
3. Post é registrado com referência a usuário e escopo.

### UC‑03 – Editar Post
1. Usuário ou admin solicita edição de post.  
2. Campos permitidos são atualizados.  
3. Sistema retorna dados atualizados.

### UC‑04 – Excluir Post
1. Usuário ou admin solicita remoção de post.  
2. Sistema marca post como `deleted` e o oculta em listagens.

### UC‑05 – Filtrar e Pesquisar
1. Usuário aplica filtros por tags, data ou organização.  
2. Sistema retorna posts correspondentes aos critérios.

## 6. Regras de Negócio
- Se `tipo_feed` = 'nucleo', campo `nucleo` é obrigatório.  
- Se `tipo_feed` = 'evento', campo `evento` é obrigatório.  
- `organizacao` é obrigatório para todos os posts.  
- Posts marcados como `deleted` não aparecem no feed.

## 7. Modelo de Dados
*Nota:* Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário. Assim, campos de timestamp e exclusão lógica não são listados individualmente.

- **Post**  
  - id: UUID  
  - autor: FK → User.id  
  - organizacao: FK → Organizacao.id  
  - tipo_feed: enum('global','usuario','nucleo','evento')  
  - nucleo: FK → Nucleo.id (opcional)  
  - evento: FK → Evento.id (opcional)  
  - conteudo: TextField  
  - image: ImageField (S3)  
  - pdf: FileField (S3)  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Feed de Publicações
  Scenario: Listar posts globais
    Given posts existentes no escopo "global"
    When GET /api/feed/?tipo_feed=global
    Then retorna lista de posts em JSON

  Scenario: Criar post com mídia
    Given usuário autenticado
    When envia POST com `conteudo` e arquivo
    Then retorna HTTP 201 e post aparece na listagem
```

## 9. Dependências / Integrações
- **Storage S3**: upload/download de arquivos.  
- **App Accounts**: autenticação e contexto de usuário.  
- **App Organizações**: validação de escopo de organização.  
- **App Núcleos** e **App Eventos**: validação de IDs de núcleo/evento.  
- **Search Engine**: índices para pesquisa por tags.  
- **Celery**: processar uploads e envio de notificações assíncronas.  
- **Sentry**: monitoramento de erros.

## 10. Anexos e Referências
- Documento fonte: Requisitos_Feed_Hubx_Atualizado.pdf

## 11. Melhorias e Extensões (Auditoria 2025‑07‑25)

### Requisitos Funcionais Adicionais
- **RF‑07** – Suportar upload de vídeos (MP4) com preview e reprodução embutida.  
- **RF‑08** – Implementar sistema de tags associadas a posts e permitir filtragem por tags.  
- **RF‑09** – Aplicar moderação automática de conteúdo com lista de palavras proibidas e marcação de posts para revisão.  
- **RF‑10** – Notificar autores quando seus posts receberem curtidas ou comentários.  

### Modelo de Dados Adicional
- `Post`: adicionar `video: FileField` (opcional) e `tags: M2M → Tag`.  
- Nova entidade `Tag` com campos: id, nome (único).  
- Nova entidade `ModeracaoPost` com campos: id, post_id, status (`pendente`,`aprovado`,`rejeitado`), motivo, avaliado_por, avaliado_em.  

### Regras de Negócio Adicionais
- Vídeos devem estar em formatos suportados (MP4, WEBM) e com tamanho máximo definido por configuração.  
- Posts com conteúdo moderado ficam ocultos até aprovação.  
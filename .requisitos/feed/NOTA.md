# Relatório do aplicativo Feed

## Visão geral

O módulo **Feed** do Hubx disponibiliza um mural de publicações com textos e mídias (imagens, PDFs, vídeos) para organizações, usuários, núcleos e eventos. A versão 1.0 dos requisitos previa listagem, criação, edição e remoção de posts, com filtros por organização e tags, upload seguro de arquivos e paginação. O código atual expande substancialmente esse escopo, incorporando moderação automática e manual, comentários, curtidas, favoritos, denúncias, reações, notificações, rate limiting, caching e coleta de métricas.

## Funcionalidades implementadas

### Postagens e mídia

- **Criação de post** – Cada post possui um `tipo_feed` (global, usuário, núcleo, evento) e pode incluir texto e um único arquivo de mídia (imagem, PDF ou vídeo). O formulário valida que apenas uma mídia é enviada e que o conteúdo ou a mídia esteja presente. Durante a gravação, a mídia é enviada ao storage via serviço `upload_media` que valida tipo e tamanho conforme extensões permitidas【111043005419319†L21-L39】. O código também define tamanho máximo para cada tipo de mídia (imagem, PDF, vídeo) via configurações e rejeita formatos não suportados【111043005419319†L28-L39】.
- **Escopos de feed** – Posts podem pertencer ao feed global, ao mural do usuário, a um núcleo ou a um evento. Regras de negócio exigem que `nucleo` seja informado quando `tipo_feed` = "nucleo" e `evento` quando `tipo_feed` = "evento"; essas validações estão implementadas no modelo e no serializer【888547345495593†L78-L82】【415540757890641†L62-L71】.
- **Tags** – Cada post pode ter múltiplas tags através de uma relação M2M. Existe um modelo `Tag` próprio no app feed【888547345495593†L14-L20】; as tags podem ser filtradas na listagem usando `tags=<lista>` e são incluídas na busca textual【415540757890641†L223-L267】.
- **Busca e filtros** – O API e as views suportam filtros por tipo de feed, organização, núcleo, evento, tags, intervalo de datas, além de busca textual (campos `conteudo` e `tags__nome`). Quando o banco é PostgreSQL, utiliza‑se `SearchVector` e `SearchRank`; para outros bancos, aplica‑se `icontains` nos termos【415540757890641†L243-L267】【164037179493221†L120-L152】. As buscas permitem termos compostos e operador OR com `|`.
- **Paginação, cache e rate limiting** – A listagem de posts utiliza paginação padrão e cache de 60 segundos para reduzir latência; a chave de cache considera o usuário e os parâmetros de filtragem【415540757890641†L270-L302】. Há rate limiting para criação de posts e leitura do feed, ajustado por um multiplicador na organização e usando a biblioteca `django_ratelimit`【415540757890641†L186-L196】【415540757890641†L286-L296】.

### Moderação e denúncias

- **Filtro de conteúdo via IA** – Antes de persistir um post, a função `pre_analise` analisa o conteúdo usando heurística de palavras proibidas para classificar como “aceito”, “suspeito” ou “rejeitado”. Se o conteúdo for rejeitado, a criação é bloqueada【415540757890641†L92-L98】【805451081551129†L15-L24】. A decisão é aplicada no modelo `ModeracaoPost`, com status inicial “pendente” para posts suspeitos ou denunciados【888547345495593†L87-L96】.
- **Denúncias** – Qualquer usuário pode denunciar um post uma única vez; o use case `DenunciarPost` cria um registro `Flag` e, ao atingir um limite configurável de denúncias (padrão 3), coloca o post em status “pendente” com motivo “Limite de denúncias atingido”【319497636125417†L13-L21】. Moderadores podem então aprovar ou rejeitar via API ou view, alterando o status e registrando o usuário avaliador e motivo【415540757890641†L342-L359】【164037179493221†L334-L353】.
- **Lista de palavras proibidas** – O método `save` do modelo `Post` verifica se o conteúdo contém palavras proibidas definidas em `settings.FEED_BAD_WORDS` e, caso positivo, seta ou mantém o status de moderação como “pendente”【888547345495593†L91-L97】.
- **Notificações de moderação** – Ao moderar posts, tasks Celery enviam notificações aos autores com o status resultante (`feed_post_moderated`)【453873148412836†L53-L65】.

### Interações: curtidas, bookmarks, comentários e reações

- **Curtidas (Like)** – Usuários podem curtir e descurtir posts. As curtidas são registradas no modelo `Like` com restrição de unicidade (`post`, `user`)【888547345495593†L98-L108】. Existe API e view para criar/remover curtida; após a interação, uma task notifica o autor do post (`feed_like`)【453873148412836†L20-L31】.
- **Bookmarks** – Permite salvar posts para leitura posterior. O modelo `Bookmark` armazena pares (`user`, `post`), e a API possui endpoints para adicionar/remover e listar bookmarks【415540757890641†L319-L329】【415540757890641†L400-L407】.
- **Comentários e respostas** – Comentários são registrados no modelo `Comment`, podendo ser respostas aninhadas via `reply_to`【888547345495593†L137-L146】. Há serializers e viewsets para criar, listar e gerenciar comentários【415540757890641†L360-L367】. A view de detalhes do post inclui formulários para comentar e curtir【164037179493221†L213-L233】.
- **Reações adicionais** – O modelo `Reacao` suporta tipos de reação “like” (curtida) e “share” (compartilhamento), permitindo registrar múltiplos tipos por usuário e post【888547345495593†L178-L195】.
- **Visualizações** – O modelo `PostView` registra abertura e fechamento de posts, armazenando tempos de leitura por usuário【888547345495593†L198-L213】.

### Notificações e métricas

- **Notificações de novas postagens** – Quando um post é criado, a task `notify_new_post` envia notificações (`feed_new_post`) a todos os usuários da organização, exceto o autor. A notificação é idempotente, guardando uma chave no cache para evitar duplicidades【453873148412836†L34-L50】.
- **Notificações de interações** – Curtidas e comentários disparam a task `notificar_autor_sobre_interacao`, que envia notificações (`feed_like` ou `feed_comment`) ao autor【453873148412836†L20-L30】.
- **Métricas Prometheus** – Counters e histograms medem quantos posts foram criados (`POSTS_CREATED`), quantas notificações foram enviadas (`NOTIFICATIONS_SENT`) e a latência de envio das notificações (`NOTIFICATION_LATENCY`)【453873148412836†L11-L18】.

### Plugins e configurações

- **FeedPluginConfig** – Permite configurar plugins de feed por organização, armazenando o caminho do módulo e a frequência de execução, indicando suporte a extensões de posts automatizados【888547345495593†L24-L40】.

## Comparação com requisitos originais

1. **Requisitos atendidos:** listagem de posts filtrada por tipo de feed e organização; criação de posts com conteúdo e mídia; edição e exclusão (soft delete) pelo autor ou administrador; upload seguro de arquivos com validação de tamanho e formato; filtragem por tags e data; paginação. Todos esses requisitos de versão 1.0 estão plenamente implementados.
2. **Melhorias implementadas:**
   - Tags associadas a posts e filtro por tags (RF‑08).
   - Upload de vídeos com preview e campo `video` no modelo (RF‑07)【888547345495593†L60-L63】.
   - Moderação automática via IA com heurística de palavras proibidas, status “pendente/aprovado/rejeitado” e logs【805451081551129†L15-L24】.
   - Sistema de denúncias e moderação manual com motivo e auditoria【319497636125417†L13-L21】【415540757890641†L342-L359】.
   - Notificações a autores quando posts recebem curtidas ou comentários e quando posts são moderados; notificações de novos posts【453873148412836†L20-L50】.
   - Curtidas, bookmarks, reações (like/share) e comentários, incluindo respostas aninhadas【888547345495593†L98-L108】【888547345495593†L178-L195】.
   - Registro de visualizações com tempos de leitura (PostView)【888547345495593†L198-L213】.
   - Rate limiting por usuário e organização e cache de listagens【415540757890641†L186-L196】【415540757890641†L270-L302】.
   - Plugin de feed por organização (`FeedPluginConfig`) e integração com notificações e métricas.
3. **Requisitos não implementados:** todos os requisitos funcionais e não funcionais do documento original foram encontrados no código; não há pendências, mas há muitas extensões que precisavam ser documentadas.

## Conclusão

O app Feed evoluiu de um simples mural de posts para uma plataforma social completa. Além das operações CRUD básicas e filtros previstos originalmente, incorpora moderação (automática e manual), denúncias, curtidas, bookmarks, comentários, reações, métricas, notificações, visualizações, rate limiting e plugins. Essas novas funcionalidades aumentam a complexidade e exigem requisitos mais detalhados. O documento de requisitos foi atualizado para a versão 1.1, incluindo as funcionalidades adicionais e requisitos não funcionais como métricas, cache e moderação por IA.

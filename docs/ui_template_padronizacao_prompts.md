# Prompts de Padronização de Templates

Este documento consolida prompts operacionais para padronizar os templates dos módulos principais da Hubx. Cada instrução assume as diretrizes globais de UI já definidas (cards com `card-header`/`card-body`, formulários com `_forms/field.html`, barras de ação padrão etc.) e aponta adaptações específicas por módulo.

## Núcleos

Você é responsável por padronizar todos os templates do módulo de Núcleos localizados em `nucleos/templates/nucleos/`, seguindo as diretrizes de UI consolidadas para formulários e listagens da Hubx.

Layout-base obrigatório: sempre que o template representar uma tela completa ou um formulário em página, envolva o conteúdo em `<div class="card">` seguido de `<div class="card-body space-y-6">`. Os `<form>` devem usar `class="space-y-6"` (ou `space-y-4` quando explicitamente compactos) e renderizar os campos via `{% include '_forms/field.html' with field=... %}` para garantir consistência de estilos e mensagens de erro. Áreas de ações (botões) precisam ficar dentro de um bloco com `class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]"`.

Checklist geral antes de sair de cada arquivo:
- Remover classes customizadas duplicadas no `<form>` e migrar para o include `_forms/field.html`.
- Garantir `card-header` com título e subtítulo quando houver, e `card-body` com o espaçamento padrão (`space-y-6` ou `space-y-4`).
- Padronizar botões destrutivos/secundários usando componentes compartilhados (`_components/cancel_button.html`, `btn btn-danger`, etc.).
- Documentar com comentário no topo quando houver uma exceção intencional ao layout-base (ex.: modais HTMX ou ações inline).

Intervenções específicas:
- `nucleo_form.html` – Use como referência oficial. Revise apenas para assegurar que o include `_forms/field.html` cubra todos os campos (sem inputs manuais) e que o bloco de ações já esteja com `gap-3` e borda superior.
- `delete.html` – Substitua o cartão customizado (`bg-[var(--bg-secondary)] ... card-sm`) por `div.card` > `div.card-body space-y-4`. Posicione o texto de alerta na `card-header`, mova o `<form>` para dentro de `card-body`, e aplique a barra de ações padrão com `justify-end gap-3`, mantendo o botão “Remover” como `btn btn-danger` ou `btn btn-primary` conforme política da UI.
- `detail.html` – Certifique-se de que todas as seções (Informações, Membros) usem `card-body space-y-6`. Atualize o bloco `id="nucleo-info-actions"` para a barra padrão (`flex justify-end gap-3 pt-4 border-t ...`) e reutilize estilos consistentes para links de ação (usar `btn btn-link` ou classes equivalentes documentadas).
- `nucleo_list.html` e `meus_list.html` – Envolva filtros e listagens dentro de cards. O formulário de busca deve virar `<form class="space-y-4">` com `_forms/field.html` para `form.q` e área de ações no padrão com botões apropriados. Garanta que a grid utilize `card-grid` com espaçamento consistente e que a paginação permaneça dentro da `card-body`.
- Parciais em `partials/` – Ajuste botões e agrupamentos para usar `flex gap-3` em vez de `space-x-*`, adicione `space-y-4` quando houver múltiplos blocos verticais e mantenha os `article.card` com `card-body` para alinhamento vertical. Para componentes HTMX (ex.: `membros_list.html`), acrescente um comentário no topo indicando que o layout “flat” dentro de grids é uma exceção autorizada por ser conteúdo dinâmico.

Revise todos os templates após as alterações para remover classes órfãs e garantir que traduções (`{% trans %}`/`{% blocktrans %}`) continuem funcionando.

## Eventos

Você será responsável por padronizar todos os templates do módulo de Eventos localizados em `eventos/templates/eventos/`, aplicando as diretrizes de UI estabelecidas para formulários, listagens e cartões.

Layout-base obrigatório: toda tela completa ou formulário em página deve usar `<article class="card">` com `<div class="card-header">` (título/subtítulo quando houver) e `<div class="card-body space-y-6">`. Os `<form>` precisam de `class="space-y-6"` (ou `space-y-4` para variações compactas) e devem renderizar campos via `{% include '_forms/field.html' with field=... %}` — nada de inputs manuais. Áreas de ações devem ficar em um bloco com `class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]"`, reutilizando botões compartilhados (`_components/back_button.html`, `btn btn-primary`, `btn btn-secondary`, etc.).

Checklist global por arquivo:
- Substituir marcações customizadas por includes `_forms/field.html` e remover estilos duplicados nos campos.
- Garantir que cards tenham `card-header` e `card-body` com espaçamento padrão (`space-y-6`/`space-y-4`).
- Usar botões destrutivos/alternativos com as classes oficiais (`btn btn-danger`, `btn btn-secondary`) e alinhar toda ação final na barra padrão com borda superior.
- Inserir comentário no topo quando uma exceção ao layout-base for intencional (ex.: componentes HTMX ou listagens internas).

Intervenções específicas:
- `evento_form.html` – Consolidar o branch `{% if object %}` para evitar duplicação: extraia apenas o contexto variável e mantenha um único formulário com `card-body space-y-6`. Confirme que `_form_fields.html` cobre todos os campos e que a barra de ações utiliza `gap-3` com borda superior.
- `avaliacao_form.html` – Reescrever o corpo do formulário usando `_forms/field.html` para `nota` e `comentario`, aplicar `form-select`/`form-textarea` via include e mover o botão para uma barra padrão (`flex justify-end gap-3 pt-4 border-t ...`).
- `delete.html` – Trocar o cartão customizado vermelho por `article.card` com `card-header` destacando o texto destrutivo e `card-body space-y-4` contendo a mensagem e o `<form class="space-y-4">`. A barra de ações deve seguir o padrão (`justify-end gap-3`), mantendo o botão principal como `btn btn-danger`.
- `detail.html` – Revisar todas as seções: aplicar `card-body space-y-6`, substituir grids de ações (`mt-6 flex ...`) por barras com `pt-4 border-t ...`, e alinhar links/botões (`btn btn-link`, `btn btn-secondary`) conforme o guia. Reescrever os formulários internos (avaliação, cancelamento) para usar `_forms/field.html` e barras de ação padronizadas. Garanta que o bloco de inscritos utilize `card-body space-y-4` e que o botão “Voltar” permaneça dentro de uma área de ação consistente.
- `evento_list.html` – Certificar-se de que filtros/lista/paginação fiquem dentro de `card-body space-y-6`. Ajustar o `card-header` para título + ações, usar `card-grid` consistente e garantir que blocks de extensão (`list_actions`, `list_footer`) respeitem o espaçamento padrão.
- `calendario.html` – Revisar cartões internos (`article.card overflow-hidden`) para usar `card-body space-y-*` em vez de `p-0` quando couber, padronizar cabeçalhos flex com classes documentadas e garantir que links de detalhes usem estilos compartilhados (`btn btn-link`/`text-sm text-[var(--primary)]`).
- `calendario_mes.html` – Ajustar o card principal para que o navegador de meses fique em uma barra de ações padronizada (com borda superior se estiver após o conteúdo). Certificar-se de que a grid mensal e a lista diária herdem `space-y-6`, e que botões como “Novo Evento” reutilizem componentes de botão existentes.
- Parciais em `partials/` – Nos arquivos HTMX (`_evento_list_content.html`, `_lista_eventos_dia.html`), alinhar listas a `card-grid` com espaçamento consistente, comentar no topo que são exceções “flat” por serem conteúdos dinamicamente injetados, e garantir que qualquer barra de ação siga o padrão (`flex gap-3`).

Ao concluir cada template, revise traduções (`{% trans %}`/`{% blocktrans %}`), remova classes órfãs e valide que os includes reutilizados continuam recebendo o contexto necessário.

## Feed

Você é responsável por padronizar todos os templates localizados em `feed/templates/feed/`, aplicando as diretrizes de formulários e cartões estabelecidas pela Hubx.

Layout-base obrigatório: sempre que um template representar uma tela completa, envolva o conteúdo em `<article class="card">` (ou `<div class="card">` quando o contexto exigir) com `card-header` para títulos/subtítulos e `card-body space-y-6` (use `space-y-4` apenas em variações compactas). Todo `<form>` deve usar `class="space-y-6"` e renderizar seus campos com `{% include '_forms/field.html' with field=... %}`; estados de erro/ajuda não devem ser escritos manualmente. A barra de ações finais precisa ser um bloco separado com `class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]"`, reutilizando botões compartilhados (`_components/cancel_button.html`, `btn btn-primary`, `btn btn-secondary`, `btn btn-danger`).

Checklist global por arquivo:
- Eliminar marcação manual de labels/inputs/erros onde ainda existem e migrar para o include `_forms/field.html`.
- Garantir que todos os cartões tenham hierarquia clara (`card-header`, `card-body space-y-*`, `card-footer`/barra de ações) e remover classes duplicadas no `<form>`.
- Atualizar botões para as classes oficiais (primário, secundário, destrutivo) e alinhar ações finais na barra padrão com borda superior.
- Inserir comentário breve no topo quando houver exceção intencional ao layout-base (ex.: componentes HTMX/inline).

Intervenções específicas:
- `nova_postagem.html` – Trocar a renderização manual de radios, textarea, chips e upload por chamadas ao parcial `_forms/field.html`/parciais especializados; mover mensagens de erro globais para um bloco único após `{% csrf_token %}` e converter a área de ações para a barra padrão com borda superior (`pt-4`) em vez do espaçamento manual atual.
- `post_update.html` – Reaproveitar o mesmo layout-base da criação: centralizar o card em vez de `section max-w-2xl`, substituir todos os `|as_widget` por includes de campo, agrupar prévias de mídia em um bloco secundário dentro do `card-body space-y-*` e usar a barra de ações padrão (sem classes manuais extras).
- `post_delete.html` – Reescrever o cartão de confirmação para usar `card-header` com o título destrutivo, `card-body space-y-4` com o texto e `<form class="space-y-4">`, e mover os botões para uma barra de ações alinhada à direita com `gap-3` e borda superior.
- `post_detail.html` – Garantir `card-body space-y-6` (não apenas `space-y-4`), substituir o formulário de comentários por `_forms/field.html` + barra de ações padrão, alinhar os botões “Editar/Remover” dentro da mesma barra (usando `btn btn-secondary`/`btn btn-danger` conforme políticas) e validar que os blocos de mídia/tags respeitem o espaçamento vertical definido.
- `feed.html`, `mural.html`, `bookmarks.html` – Envolver filtros e listagens em cards completos (`card-header` + `card-body space-y-6`), remover `py-12 card px-4`, e aplicar o padrão de grid/paginação consistente nas inclusões (`_grid.html`, `_post_list.html`).
- Hero actions (`hero_actions*.html`) – Atualizar os containers de botões para `flex gap-3` (ou classes utilitárias documentadas), garantir uso de componentes de botão consistentes e incluir comentários se mantiverem links externos/`target="_blank"` como exceção aprovada.
- Parciais de listagem (`_grid.html`, `_post_list.html`) – Revisar `article.card` internos para usar `card-body space-y-6`, ajustar badges/botões para classes compartilhadas e, quando estiverem dentro de HTMX, adicionar comentário indicando a exceção ao layout-base completo.
- Parciais interativos (`_comment.html`, `_moderacao.html`, `_like_button.html`) – Uniformizar botões secundários/destrutivos com as classes oficiais, aplicar `flex gap-3` nas ações, e usar `_forms/field.html` nos formulários HTMX (ex.: motivo da rejeição) quando o campo não for puramente textual inline.

Revise cada template após as alterações para remover classes órfãs, garantir que as traduções (`{% trans %}`, `{% blocktrans %}`) continuem funcionando e confirmar que os includes recebem o contexto necessário.

## Configurações

Você será responsável por alinhar todos os templates localizados em `configuracoes/templates/configuracoes/` às diretrizes de padronização de formulários e cartões adotadas pela Hubx.

Layout-base obrigatório: telas completas e formulários devem usar `<article class="card">` (ou `<div class="card">` quando houver compatibilidade com o CSS existente), contendo `card-header` com título/subtítulo e `card-body space-y-6`. Todo `<form>` deve ter `class="space-y-6"` (ou `space-y-4` somente quando explicitamente compacto) e renderizar campos via `{% include '_forms/field.html' with field=... %}` para garantir consistência de inputs, mensagens de erro e estados. As áreas de ação finais precisam ficar dentro de um bloco dedicado com `class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]"`, reutilizando os componentes de botão compartilhados (`_components/cancel_button.html`, `btn btn-primary`, `btn btn-secondary`, `btn btn-danger`).

Checklist global por arquivo:
- Remover marcação manual de labels/erros e migrar para `_forms/field.html` (inclusive em grids).
- Revisar cartões para garantir `card-header` + `card-body space-y-*` e eliminar utilitários redundantes (`bg-[var(--bg-elevated)] border ...` já providos por `.card`).
- Centralizar a exibição de erros globais em um único bloco padrão (`alert alert-error`) imediatamente após `{% csrf_token %}`.
- Padronizar todas as barras de ação com borda superior, `gap-3` e alinhamento `justify-end`, substituindo `text-right`/`items-center` personalizados.
- Inserir comentário breve no topo quando o template representar uma exceção deliberada (ex.: formulários HTMX in-page).

Intervenções específicas:
- `configuracao_form.html` – Converter o `section` externo para `article.card` com `card-body space-y-6`; mover a seleção de abas para um `card-header` e garantir que os includes (`preferencias.html`, `seguranca.html`) recebam o container padrão. Ajustar o `main` para usar apenas `container py-6` se necessário, evitando classes redundantes.
- `operador_form.html` – Substituir a grid manual por chamadas a `_forms/field.html`, inclusive para os campos de senha. Consolidar as mensagens de erro em `alert alert-error`. Atualizar o bloco de botões para a barra padrão (`flex justify-end gap-3 pt-4 border-t ...`) e remover classes duplicadas do `<form>`/card.
- `operadores_list.html` – Garantir que o card principal tenha `card-header` com título/subtítulo e, se houver ações, movê-las para uma barra superior ou inferior padronizada. Padronizar cada item da lista para `article.card` com `card-body space-y-4`, evitando bordas customizadas. Ajustar o estado vazio para o mesmo padrão visual (`card-body space-y-4` + `border-dashed`).
- `_partials/preferencias.html` – Manter como exceção HTMX documentada (adicionar comentário). Converter os botões “Testar” para uma barra de ações reutilizável (`flex gap-3`) logo após cada conjunto de campos e atualizar o rodapé do formulário para a barra padrão com borda superior (`pt-4`). Substituir a `errorlist` customizada por `alert alert-error`.
- `_partials/seguranca.html` – Aplicar o mesmo tratamento de erros, migrar o rodapé do formulário para a barra padrão e separar a seção de 2FA em um card ou `div` com `card-body space-y-4` coerente, utilizando botões (`btn btn-secondary`, `btn btn-primary`) com `gap-3`. Adicionar comentário indicando que o formulário é recarregado via HTMX.
- `_partials/operadores_action.html` – Validar que o botão use apenas utilitários oficiais (`btn btn-primary flex gap-2 items-center`) e alinhar com as hero actions padronizadas; remover classes redundantes se houver.

Após cada ajuste, revise traduções (`{% trans %}`/`{% blocktrans %}`), garanta que includes recebam o contexto necessário (`hero_title`, `cancel_component_config`, etc.) e elimine classes ou containers órfãos que se tornarem desnecessários com o novo layout.

## Tokens

Você será responsável por aplicar as diretrizes de padronização de formulários e cartões a todos os templates em `tokens/templates/tokens/`.

Layout-base obrigatório: telas completas devem usar `<article class="card">` (ou `<div class="card">` quando necessário) com `card-header` para títulos/subtítulos e `card-body space-y-6`. Formulários precisam de `class="space-y-6"` (use `space-y-4` apenas em fluxos claramente compactos) e devem renderizar campos com `{% include '_forms/field.html' with field=... %}`. As áreas de ação finais sempre ficam em um bloco com `class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]"`, reutilizando componentes/botões padrão (`btn btn-primary`, `btn btn-secondary`, `btn btn-danger`, `_components/back_button.html`).

Checklist global por arquivo:
- Promover títulos/subtítulos que hoje estão dentro de `card-body` para um `card-header` consistente e remover utilitários redundantes (`px-*`, `mt-*`) já cobertos pelo card.
- Centralizar mensagens de status/erro em um único padrão (`alert alert-success`, `alert alert-error`) em vez de `div`s ad-hoc nos parciais de resultado.
- Padronizar botões de navegação/retorno em barras de ação com `gap-3` e borda superior; evitar `text-right` isolado ou `footer` desalinhado.
- Adicionar comentário no topo de templates HTMX explicando por que permanecem “flat” (ex.: quando o conteúdo é injetado dentro de um card maior).

Intervenções específicas:
- `gerar_token.html` – Mover o header atual para `card-header`, manter `card-body space-y-6` e garantir que o resultado HTMX continue dentro do corpo com espaçamento consistente; alinhar o footer com o botão de voltar usando a barra padrão de ações (trocar `mt-6` + footer solto por `flex justify-end gap-3 pt-4 ...`).
- `validar_token.html` – Adicionar `space-y-6` ao `card-body`, substituir o bloco `text-right` por uma barra de ações padronizada e mover o link de retorno para o mesmo padrão de footer, garantindo que o formulário HTMX continue funcional.
- `token_list.html` – Transformar o container externo em `section` sem padding duplicado e promover o card interno para usar `card-header` (título + ações) e `card-body space-y-6`. Revisar a tabela para remover classes redundantes (`card px-4`, `card-sm`) e padronizar o estado vazio como bloco dentro do `card-body`. A barra de retorno deve usar o padrão de ações com `flex justify-end gap-3` em vez de um `<div>` isolado.
- `tokens.html` – Garantir que a área principal (`#tokens-conteudo`) aplique o layout-base quando não estiver renderizando parciais, encapsulando `token_list.html` em um card completo. Se `partial_template` já for um card, documente via comentário que a responsabilidade fica com o parcial.
- `_resultado.html` – Substituir os blocos de feedback por componentes de alerta padronizados (`alert alert-success` / `alert alert-error`) e adicionar um wrapper com `space-y-4` quando houver múltiplas mensagens, mantendo a acessibilidade HTMX (`role="status"`/`role="alert"`).
- `hero_action.html` – Confirmar que o botão use apenas utilitários padronizados (`btn btn-primary`) e adicionar comentário se o tamanho `btn-sm` permanecer como exceção aprovada para a hero action.

Ao finalizar cada template, remova classes órfãs, garanta que traduções (`{% trans %}`/`{% blocktrans %}`) continuem funcionando e valide que os includes recebem o contexto necessário.

## Notificações

Você deve padronizar todos os templates em `notificacoes/templates/notificacoes/`, alinhando-os às diretrizes oficiais de formulários e cartões da Hubx.

Layout-base obrigatório: toda tela completa deve usar `<article class="card">` (ou `<div class="card">` quando exigido pelo CSS existente) com `card-header` para título/subtítulo e `card-body space-y-6`. Formularios inteiros recebem `class="space-y-6"` (usar `space-y-4` apenas em variantes compactas) e todos os campos são renderizados via `{% include '_forms/field.html' with field=... %}`. A área de ações finais fica em um bloco separado com `class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]"`, reutilizando botões/componentes compartilhados (`btn btn-primary`, `btn btn-secondary`, `btn btn-danger`, `_components/cancel_button.html`).

Checklist global por arquivo:
- Remover bordas/paddings redundantes (`card-sm`, `border border-[var(--border)]`) quando o cartão padrão já cobre.
- Centralizar mensagens de sucesso/erro em componentes `alert` padrão imediatamente após `{% csrf_token %}` nos formulários.
- Garantir que filtros e resultados compartilhem o mesmo card (`header` com título, `body` com formulário + tabela) e que botões de ação não fiquem inline sem a barra com `gap-3`.
- Adicionar comentário no topo dos parciais HTMX explicando a exceção ao layout completo (ex.: tabelas atualizadas dinamicamente).

Intervenções específicas:
- `templates_list.html` – Transformar o container principal em `article.card` com `card-header` (título + hero action) e `card-body space-y-6`. Substituir o wrapper `overflow-x-auto ... card-sm` por uma tabela dentro do `card-body` com espaçamento padrão, mover botões “Ativar/Desativar/Excluir” para um `flex gap-3` consistente e usar `btn` oficiais (evitando links com `text-primary`). Estado vazio deve virar bloco dentro do card com `space-y-4`.
- `template_form.html` – Confirmar que o `card-header` apresente título/subtítulo conforme o contexto (novo x edição) e que o `<form>` use `space-y-6`. Centralizar erros globais com `alert` e garantir `gap-3` na barra de ações, removendo `space-y-4` redundante.
- `template_confirm_delete.html` – Reescrever para `article.card` com `card-header` destacando o título destrutivo. Manter o texto de confirmação no `card-body space-y-4`, usar `<form class="space-y-4">` com `_forms/field.html` quando houver campos (no momento apenas `csrf`) e alinhar os botões na barra padrão (`btn btn-danger` + componente de cancelamento).
- `logs_list.html` / `historico_list.html` – Unificar filtro e tabela no mesmo card: `card-header` com título, `card-body space-y-6` contendo `<form class="space-y-4">` (filtros renderizados via include) e uma barra de ações separada com `btn btn-primary`. O container que recebe HTMX (`#logs-container`, `#historico-container`) deve permanecer dentro do `card-body`, precedido de comentário justificando a atualização dinâmica.
- `logs_table.html` / `historico_table.html` – Remover `card-sm` e classes extras, deixando apenas `<div class="overflow-x-auto">` dentro do card pai. Adicionar comentário no topo indicando que o parcial é injetado via HTMX e, se necessário, envolver a tabela em `div class="card-body space-y-4"` quando reutilizada isoladamente. Garantir que paginação herde o espaçamento padrão (`mt-6` → `space-y-4` ou barra de ações).
- `metrics.html` – Converter os dois cards em estrutura padrão: o filtro vira `card-header` ou bloco inicial com `<form class="space-y-4">` e barra de ações padronizada; a área de métricas fica em `card-body space-y-6`, com listas/contagens organizadas em `space-y-4`. Avaliar uso de description list (`dl`) ou `<table>` para métricas, mantendo consistência com outros módulos.
- `hero_action.html` – Verificar que o botão utilize apenas utilitários padronizados (`btn btn-primary flex gap-2 items-center`) e adicionar comentário se `btn-sm` for necessário como exceção aprovada.
- Parciais de linhas (`logs_rows.html`, `historico_rows.html`) – Adicionar comentário inicial explicando que são renderizados dentro das tabelas HTMX e garantir que qualquer conteúdo adicional (mensagens de vazio) use classes coerentes (`text-[var(--text-secondary)]`, `px-4 py-6 text-center`).

Ao concluir cada arquivo, remova classes órfãs, confira traduções (`{% trans %}`, `{% blocktrans %}`) e valide que os includes continuem recebendo o contexto apropriado (`cancel_component_config`, `request.GET.urlencode`, etc.).


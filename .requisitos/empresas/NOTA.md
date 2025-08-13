# Relatório do aplicativo Empresas

## Visão geral

O app **Empresas** é responsável por gerenciar o cadastro de organizações parceiras no Hubx, incluindo dados básicos, tags, localização e informações adicionais. A versão de requisitos 1.0 descrevia apenas operações CRUD básicas, busca por tags e unicidade de CNPJ. A análise do código evidenciou um conjunto de funcionalidades bem mais amplo, contemplando validação automática de CNPJ, histórico de alterações, avaliações de usuários, favoritos, contatos, validação assíncrona e integração com o feed e o sistema de notificações.

## Funcionalidades implementadas

### Cadastro e edição de empresas

- **Campos principais**: cada empresa possui ID, usuário responsável, organização vinculada, nome, CNPJ, tipo, município, estado, logo opcional, descrição, palavras‑chave e tags. Há ainda campos adicionais `validado_em` (data de validação), `fonte_validacao` e `versao` para versionamento【429103258910557†L40-L63】.
- **Validação de CNPJ**: o modelo valida o formato do CNPJ usando a biblioteca `validate_docbr`. Um campo `validado_em` indica quando a empresa foi validada e `fonte_validacao` armazena a origem da validação. Uma task Celery `validar_cnpj_empresa` consulta um serviço externo e atualiza esses campos【931225567035249†L16-L31】. O formulário sanitiza e formata o CNPJ, impede valores duplicados e mascarados【450003777006958†L43-L55】.
- **Soft delete e recuperação**: as empresas usam exclusão lógica (`SoftDeleteModel`). Views e API permitem restaurar registros soft deletados e, para administradores ou root, purgá‑los definitivamente【138211013721496†L146-L175】. Cada exclusão, restauração ou purga gera um registro em `EmpresaChangeLog` e incrementa métricas Prometheus (ex.: `empresas_purgadas_total`)【138211013721496†L47-L57】【138211013721496†L168-L186】.
- **Histórico de alterações**: o serviço `registrar_alteracoes` grava, em `EmpresaChangeLog`, todas as mudanças nos campos principais, comparando o valor antigo e o novo. Para o campo CNPJ, apenas os últimos dígitos são registrados para preservar privacidade【573755385539507†L100-L129】. O histórico pode ser consultado por administradores via view/API【104399097495256†L181-L198】【138211013721496†L139-L147】.
- **Versionamento**: campo `versao` incrementa a cada modificação; não é exposto para edição e permite rastrear alterações【429103258910557†L60-L63】.

### Tags e busca

- **Hierarquia de tags**: as tags agora suportam categorias (`prod` ou `serv`) e um campo `parent` permite criar árvores de tags【429103258910557†L15-L31】. Views permitem listar, criar, editar e excluir tags com filtros por categoria e busca de nome【104399097495256†L128-L146】.
- **Busca avançada**: a função `search_empresas` aplica filtros por nome, município, estado, organização, palavras‑chave e tags. Para a busca textual, utiliza `SearchVector` e `SearchRank` quando o banco é PostgreSQL ou, em outros bancos, pesquisa no campo `search_vector` carregado no modelo【573755385539507†L24-L74】. O resultado é distinto e pode ser ordenado por relevância. Existem também formulários select2 para pesquisar empresas e tags no frontend【450003777006958†L115-L126】.

### Contatos e favoritos

- **Gestão de contatos**: cada empresa pode ter múltiplos contatos. O modelo `ContatoEmpresa` registra nome, cargo, e‑mail, telefone e um flag `principal`. A lógica no método `save` garante que apenas um contato principal exista por empresa【429103258910557†L113-L137】. As views permitem adicionar, editar e remover contatos e retornam respostas JSON para integração com HTMX【104399097495256†L307-L347】.
- **Favoritos**: usuários podem marcar empresas como favoritas (modelo `FavoritoEmpresa`). A API possui endpoints para favoritar, desfavoritar e listar empresas favoritas de um usuário, incrementando métricas de favoritos adicionados/removidos【138211013721496†L78-L106】. O serializer inclui um campo `favoritado` calculado para indicar se a empresa é favorita no contexto da requisição【345985525491424†L14-L41】.

### Avaliações e integração com feed

- **Avaliações**: usuários podem avaliar empresas com notas de 1 a 5 e comentário opcional. Cada usuário pode avaliar uma empresa apenas uma vez; a média das avaliações é calculada no modelo através de `media_avaliacoes`【429103258910557†L108-L112】. As views e API oferecem criação e edição de avaliações, retornando fragmentos HTMX atualizados【104399097495256†L203-L267】. 
- **Notificações e feed**: ao registrar uma nova avaliação, dispara‑se o sinal `nova_avaliacao`, que aciona tasks para notificar o usuário responsável e criar posts no feed quando a nota for ≥ 4【931225567035249†L14-L99】. Há também uma task `criar_post_empresa` que publica no feed quando uma nova empresa é cadastrada【931225567035249†L54-L72】.

### APIs e permissões

- **API REST**: o `EmpresaViewSet` oferece operações CRUD com permissões condicionadas: apenas o usuário autor ou administradores podem atualizar, excluir ou restaurar empresas【138211013721496†L64-L76】. A API suporta filtros por nome, palavras‑chave, tags e busca textual, além de endpoints especiais para favoritar, listar favoritos, registrar avaliações, listar avaliações, consultar histórico de alterações, restaurar e purgar empresas【138211013721496†L78-L171】.
- **Validação e sanitização**: o formulário `EmpresaForm` remove caracteres perigosos de tags e formata o CNPJ; o método `clean_cnpj` valida e formata o CNPJ, impedindo duplicidades【450003777006958†L43-L55】. As tags são criadas ou recuperadas sanitizando o nome com uma função `sanitize_tag_name`【450003777006958†L7-L11】【450003777006958†L65-L73】.
- **Controle de acesso**: mixins `ClienteGerenteRequiredMixin` e `NoSuperadminMixin` impedem super administradores de operar em empresas; a busca retorna registros conforme o tipo de usuário (superuser, admin, coordenador, nucleado), limitando a visualização de empresas apenas às organizações às quais o usuário pertence【573755385539507†L24-L38】.

## Comparação com requisitos originais

*Todos* os requisitos da versão 1.0 – listagem, criação, edição, exclusão, busca por palavras‑chave e tags, unicidade de CNPJ e vinculação à organização – estão contemplados no código. Além disso, as melhorias RF‑06 (histórico de alterações) e RF‑07 (avaliações) estão totalmente implementadas através das classes `EmpresaChangeLog` e `AvaliacaoEmpresa` e suas respectivas views e APIs【429103258910557†L138-L176】. 

Entretanto, a aplicação vai muito além do escopo original:

1. **Validação automática de CNPJ** e registro de data e fonte de validação, com tarefa Celery. 
2. **Campo de versão (`versao`)** para versionamento interno do registro. 
3. **Favoritos**: marcar e desmarcar empresas favoritas, listagem e métricas. 
4. **Gestão de contatos** para cada empresa, garantindo contato principal único. 
5. **Hierarquia e categorização de tags** (com suporte a pai/filho). 
6. **Busca full‑text avançada** com ranking e fallback para bancos sem Postgres. 
7. **Integração com feed**: posts automáticos em feed global ao cadastrar empresa ou receber avaliação positiva. 
8. **Restaurar e purgar empresas soft deletadas**, com métricas de operações e permissões adequadas. 
9. **Notificações assíncronas** ao responsável quando uma avaliação é feita. 
10. **Controle de acesso refinado**: diferentes níveis de acesso para super administradores, administradores, coordenadores e nucleados.

Esses pontos não constavam no documento original e precisam ser registrados como novos requisitos funcionais e não funcionais.

## Conclusão

O app Empresas evoluiu de um cadastro simples para um sistema robusto de gestão, com validação externa, histórico de alterações, avaliações e feedbacks, favoritos, hierarquia de tags, busca avançada, controle de acesso sofisticado e integração com outros módulos. Todos os requisitos do documento anterior foram atendidos, e diversas funcionalidades extra foram identificadas. A atualização do documento de requisitos para a versão 1.1 incorpora esses novos recursos, definindo-os formalmente e ampliando os requisitos não funcionais para abranger desempenho, segurança, observabilidade e integração assíncrona.

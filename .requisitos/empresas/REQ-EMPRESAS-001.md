---
id: REQ-EMPRESAS-001
title: Requisitos Empresas Hubx
module: empresas
status: Em vigor
version: "1.1.0"
authors: [preencher@hubx.space]
created: "2025-07-25"
updated: "2025-08-13"
owners: [preencher]
reviewers: [preencher]
tags: [backend]
related_docs: []
dependencies: []
---

## 1. Visão Geral

O aplicativo **Empresas** permite gerenciar empresas vinculadas a organizações no sistema Hubx, abrangendo cadastro, consulta, atualização e exclusão lógica, além de recursos avançados de busca, tags, histórico de alterações, avaliações, favoritos, contatos e integração com outros módulos.

## 2. Escopo

- **Inclui**:
  - Listar e visualizar empresas com filtros por organização, município, estado, palavras-chave e tags.
  - Cadastro de novas empresas (nome, CNPJ, tipo, localização, logo, descrição, palavras-chave, tags e campos de validação).
  - Edição de dados cadastrais e restauração de registros excluídos.
  - Exclusão lógica (soft delete), restauração e purga definitiva (hard delete).
  - Sistema de tags hierárquicas (categorias produto e serviço) para pesquisa e categorização.
  - Histórico de alterações de dados e versionamento interno.
  - Cadastro de contatos de empresa (nome, cargo, e-mail, telefone, principal) com garantia de um contato principal por empresa.
  - Favoritar e desfavoritar empresas; listagem de favoritos.
  - Avaliação de empresas com notas de 1 a 5 e comentários; cálculo da média das avaliações; uma avaliação por usuário por empresa.
  - Busca textual avançada com ordenação por relevância e filtros combinados.
  - Integração com feed: posts automáticos sobre novas empresas e avaliações positivas.
  - Integração com notificações: notificação ao responsável quando uma nova avaliação é registrada.
- **Exclui**:
  - Processos de faturamento ou pagamento.
  - Gerenciamento de usuários e organizações (tratados por outros apps).

## 3. Requisitos Funcionais

### Operações básicas

- **RF-01** — Listar empresas com paginação e filtros por organização, município, estado, palavras-chave, tags e busca textual. Responder via parâmetros `request.GET`.
- **RF-02** — Cadastrar empresa com validação de CNPJ único. O sistema deve formatar e validar o CNPJ usando biblioteca apropriada. Em caso de duplicidade, retorna erro HTTP 400.
- **RF-03** — Editar dados de uma empresa existente. Apenas o usuário responsável ou administradores podem editar. Campos não informados permanecem inalterados.
- **RF-04** — Excluir empresa (soft delete) pelo usuário responsável ou administradores. O registro excluído não aparece nas listagens e pode ser restaurado posteriormente.
- **RF-05** — Pesquisar empresas por palavras-chave, tags, nome, município, estado e organização. Deve aceitar busca textual (`q`) com ordenação por relevância.
- **RF-06** — Restaurar empresas excluídas. Apenas o autor, administradores ou root podem restaurar. Após restaurar, registrar no log de alterações e atualizar métricas.
- **RF-07** — Purgar definitivamente empresas excluídas. Somente administradores ou root podem purgar. Registrar a operação no log e métricas.
- **RF-08** — Registrar histórico de alterações (quem alterou, quando e quais campos). Para campos sensíveis como CNPJ, mascarar o valor antigo/novo, mantendo apenas os últimos dígitos.
- **RF-09** — Versionar empresas; cada alteração incrementa o campo `versao` automaticamente.

### Tags e busca

- **RF-10** — Gerenciar tags hierárquicas: listar, criar, editar e excluir tags com categoria `prod` ou `serv` e relação de parentesco (`parent`). A busca de tags deve suportar autocomplete.
- **RF-11** — Filtrar listagens por tags e permitir múltiplas tags (AND). A busca textual deve empregar `SearchVector` e `SearchRank` para PostgreSQL ou utilizar o campo `search_vector` para outros bancos.

### Contatos e favoritos

- **RF-12** — Cadastrar, editar e remover contatos de empresa. Cada contato deve registrar nome, cargo, e-mail, telefone e o indicador `principal`. Garantir que apenas um contato principal exista por empresa; ao salvar um novo contato principal, remover a marcação dos demais.
- **RF-13** — Marcar empresa como favorita ou desfavoritar. Permitir listar empresas favoritas do usuário autenticado. Registrar métricas de favoritos adicionados e removidos.

### Avaliações e feedback

- **RF-14** — Permitir que usuários avaliem empresas com nota de 1 a 5 e comentário. Cada usuário pode enviar apenas uma avaliação por empresa e pode editá-la posteriormente. Calcular a média das avaliações por empresa.
- **RF-15** — Notificar o usuário responsável da empresa quando uma nova avaliação for registrada. Para notas ≥ 4, gerar automaticamente um post no feed global da organização.

### Integrações e API

- **RF-16** — Oferecer API REST completa (ModelViewSet) para empresas com endpoints de listagem, criação, leitura, atualização, soft delete, restauração e purga. Disponibilizar endpoints adicionais para favoritar/desfavoritar, listar favoritos, registrar avaliações, listar avaliações, consultar histórico de alterações e validação do CNPJ. Controlar permissões por tipo de usuário (autor, admin, root, coordenador, nucleado).
- **RF-17** — Integrar com tasks Celery para validação de CNPJ, notificações de avaliações e criação de posts no feed. As tasks devem registrar erros no Sentry e realizar retry em falhas temporárias.
- **RF-18** — Atualizar o feed global ao cadastrar nova empresa (publicação automática).

## 4. Requisitos Não Funcionais

### Performance
- **RNF-01** Listagens de empresas devem responder em p95 ≤ 300 ms, considerando filtros e busca textual. Utilizar `select_related`, `prefetch_related` e indexes apropriados.

### Segurança & LGPD
- **RNF-02** Garantir unicidade do CNPJ e sanitização dos campos de tags e contatos; mascarar CNPJ nos logs. Controlar acesso às operações (CRUD, avaliação, favoritos, histórico) via permissões. Somente usuários autenticados podem avaliar ou favoritar.
- **RNF-03** Registrar mudanças no CNPJ de forma mascarada; armazenar logos em storage externo seguro (S3); anonimizar dados pessoais em logs conforme LGPD.

### Observabilidade
- **RNF-04** Integrar com Sentry para logging de erros e Prometheus/Grafana para métricas de favoritos, restauração e purga. As tasks Celery devem registrar latência e falhas.

### Acessibilidade & i18n
- …

### Resiliência
- **RNF-05** A validação de CNPJ deve utilizar serviço externo confiável e registrar a fonte de validação. Em caso de indisponibilidade, a validação pode ser reprocessada posteriormente.

### Arquitetura & Escala
- **RNF-06** Código modular e documentado, com cobertura de testes ≥ 90 %. Manter a lógica de busca e registro de alterações em serviços isolados.
- **RNF-07** Todos os modelos devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`) e de `SoftDeleteModel` para exclusão lógica. Campos de timestamp e exclusão não precisam ser listados individualmente.

## 5. Casos de Uso

### UC-01 — Listar Empresas
1. Usuário acessa o endpoint de listagem de empresas.
2. Aplica filtros de nome, município, estado, organização, tags ou palavras-chave.
3. Sistema realiza a busca textual (quando solicitado) e retorna página de resultados paginados ordenados conforme a relevância.

### UC-02 — Criar Empresa
1. Usuário preenche formulário com dados da empresa (nome, CNPJ, tipo, localização, descrição, palavras-chave e tags).
2. Sistema valida CNPJ, formata tags, salva a empresa e associa o usuário e organização atual.
3. Cria post automático no feed global e agenda task para validação de CNPJ.
4. Retorna HTTP 201 com os dados criados.

### UC-03 — Editar Empresa
1. Usuário responsável ou administrador solicita edição da empresa.
2. Sistema registra os valores atuais em memória e atualiza somente os campos fornecidos.
3. Após salvar, registra as mudanças em `EmpresaChangeLog` e incrementa a versão.
4. Retorna HTTP 200 com os dados atualizados.

### UC-04 — Excluir, Restaurar e Purgar Empresa
1. Usuário responsável ou administrador solicita exclusão (soft delete) de uma empresa.
2. Sistema marca o registro como `deleted=True` e registra no log; retorna HTTP 204.
3. Administradores podem acessar endpoint de restauração, que reverte o `deleted` e registra no log.
4. Administradores ou root podem acessar endpoint de purga definitiva; o sistema remove o registro do banco e registra a ação.

### UC-05 — Avaliar Empresa
1. Usuário autenticado acessa a página de avaliação de uma empresa.
2. Se já tiver avaliado, pode editar a avaliação; caso contrário, preenche nota (1-5) e comentário.
3. Sistema salva a avaliação, calcula a nova média, envia notificação ao responsável e, se a nota for ≥ 4, cria um post no feed.
4. Retorna HTTP 201/200 com a avaliação salva.

## 6. Regras de Negócio

- O CNPJ deve ser único em todo o sistema e seguir o formato brasileiro, sendo validado ao criar ou editar.
- A empresa deve estar vinculada a uma organização e possuir um usuário responsável (autor).
- Apenas o usuário responsável ou administradores podem editar, excluir, restaurar ou purgar uma empresa.
- Cada usuário pode avaliar uma empresa apenas uma vez; podem editar sua avaliação posteriormente.
- Somente um contato pode ser marcado como principal por empresa; e-mails de contatos são únicos por empresa.
- Um usuário pode favoritar uma empresa uma vez; desfavoritar remove o registro.

## 7. Modelo de Dados

### Empresas.Empresa
Descrição: Cadastro de empresas.
Campos:
- `id`: UUID
- `usuario`: FK → User
- `organizacao`: FK → Organizacao
- `nome`: string
- `cnpj`: string — único
- `tipo`: string
- `municipio`: string
- `estado`: string
- `logo`: imagem
- `descricao`: texto
- `palavras_chave`: texto
- `tags`: M2M → Tag
- `validado_em`: datetime
- `fonte_validacao`: string
- `versao`: inteiro
Constraints adicionais:
- Herda de `TimeStampedModel` e `SoftDeleteModel`.

### Empresas.Tag
Descrição: Tag para classificação de empresas.
Campos:
- `id`: UUID
- `nome`: string
- `categoria`: enum(`prod`/`serv`)
- `parent`: FK → Tag (opcional)
Constraints adicionais:
- Herda de `TimeStampedModel`.

### Empresas.ContatoEmpresa
Descrição: Contato associado a uma empresa.
Campos:
- `id`: UUID
- `empresa`: FK → Empresa
- `nome`: string
- `cargo`: string
- `email`: string
- `telefone`: string
- `principal`: boolean
Constraints adicionais:
- Herda de `TimeStampedModel`.

### Empresas.EmpresaChangeLog
Descrição: Registro de alterações de empresa.
Campos:
- `id`: UUID
- `empresa`: FK → Empresa
- `usuario`: FK → User
- `campo_alterado`: string
- `valor_antigo`: texto (mascarado quando sensível)
- `valor_novo`: texto (mascarado quando sensível)
- `alterado_em`: datetime
Constraints adicionais:
- Herda de `SoftDeleteModel`.

### Empresas.AvaliacaoEmpresa
Descrição: Avaliação de empresa por usuário.
Campos:
- `id`: UUID
- `empresa`: FK → Empresa
- `usuario`: FK → User
- `nota`: inteiro (1-5)
- `comentario`: texto
Constraints adicionais:
- Herda de `TimeStampedModel` e `SoftDeleteModel`.

### Empresas.FavoritoEmpresa
Descrição: Registro de empresa favoritada.
Campos:
- `id`: UUID
- `usuario`: FK → User
- `empresa`: FK → Empresa
Constraints adicionais:
- Herda de `TimeStampedModel` e `SoftDeleteModel`.

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Histórico de alterações
  Scenario: Registrar mudança de CNPJ com máscara
    Given uma empresa existente com CNPJ “12.345.678/0001-90”
    When o administrador edita o CNPJ para “23.456.789/0001-00”
    Then um registro é criado em EmpresaChangeLog
    And o valor_antigo registrado é “***90” e o valor_novo é “***00”

Feature: Favoritar e desfavoritar empresa
  Scenario: Adicionar empresa aos favoritos
    Given um usuário autenticado visualiza uma empresa
    When solicita a ação de favoritar
    Then um registro FavoritoEmpresa é criado e a métrica “empresas_favoritos_total” é incrementada

  Scenario: Remover dos favoritos
    Given uma empresa já favoritada pelo usuário
    When solicita a ação de desfavoritar
    Then o registro é marcado como deleted e a métrica “empresas_favoritos_total” é decrementada

Feature: Avaliar empresa e publicar no feed
  Scenario: Avaliação positiva
    Given um usuário avalia uma empresa com nota 5
    When a avaliação é salva
    Then a média de avaliações é atualizada
    And o responsável pela empresa é notificado
    And um post é criado no feed global com a nota

```

## 9. Dependências e Integrações

- **App Accounts**: identificação do usuário responsável e permissões.
- **App Organizações**: validação da organização vinculada.
- **App Feed**: criação de posts automáticos para novas empresas e avaliações positivas.
- **App Notificações**: envio de notificações para usuários responsáveis.
- **Serviço externo de validação de CNPJ**: consulta de validade e origem de dados.
- **Search Engine**: uso de PostgreSQL full-text ou fallback no campo `search_vector` para busca.
- **Storage (S3)**: armazenamento de logos de empresa.
- **Prometheus/Grafana**: métricas de favoritos, purgas e restaurações.
- **Sentry**: monitoramento de erros e falhas em tasks.

## Anexos e Referências
...

## Changelog
- 1.1.0 — 2025-08-13 — Normalização estrutural.

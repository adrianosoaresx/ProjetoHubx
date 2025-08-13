# Guia do Usuário – Organizações

### Visão geral
O módulo Organizações permite administrar entidades do Hubx. Cada organização possui dados cadastrais, imagens, contatos e associações com usuários, núcleos, eventos, empresas e posts.

### Principais funcionalidades
1. Criar uma nova organização.
2. Editar dados existentes.
3. Inativar, reativar e excluir organizações.
4. Listar e buscar por nome ou slug.
5. Consultar histórico de alterações e atividades.

### Fluxos
#### 1. Criar organização
1. Usuário root envia `POST /api/organizacoes/` com nome e CNPJ.
2. Sistema gera `slug` único, valida CNPJ e salva dados.
3. Avatar e capa podem ser enviados no mesmo payload (`multipart/form-data`).
4. Membros recebem notificação por e‑mail.

#### 2. Editar organização
1. Usuário root envia `PATCH /api/organizacoes/<id>/` com campos a atualizar.
2. Alterações relevantes geram log e notificações.
3. Slug e CNPJ passam por validação e normalização.

#### 3. Inativar ou reativar
1. Usuário root chama `PATCH /api/organizacoes/<id>/inativar/` ou `/reativar/`.
2. Status `inativa` e data correspondente são atualizados.
3. Logs registram a ação e notificam membros.

#### 4. Excluir organização
1. Usuário root executa `DELETE /api/organizacoes/<id>/`.
2. Registro é marcado como `deleted`; dados permanecem para auditoria.

#### 5. Listar e buscar
1. Usuário root ou admin consulta `GET /api/organizacoes/?search=<texto>&inativa=true|false&ordering=nome`.
2. Resultado é paginado automaticamente.

#### 6. Histórico de alterações
1. `GET /api/organizacoes/<id>/history/` retorna últimas mudanças e atividades.
2. `GET /api/organizacoes/<id>/history/?export=csv` gera arquivo CSV para download.

### Permissões
- Root: pode criar, editar, inativar, reativar, excluir e consultar histórico de qualquer organização.
- Admin de organização: pode listar, visualizar e acessar histórico da própria organização.
- Demais perfis: acesso negado às APIs.

### Mensagens e erros comuns
- `Formato de imagem não suportado.` – enviado quando avatar ou capa não atendem à lista de extensões permitidas.
- `Imagem excede o tamanho máximo permitido.` – tamanho da imagem maior que o limite configurado.
- `CNPJ inválido.` – valor do CNPJ não passou pela validação.
- `permission_denied` – usuário sem permissão adequada.

### Exemplos de uso
- Criar: `POST /api/organizacoes/ {"nome": "Minha ONG", "cnpj": "00.000.000/0000-00"}`
- Buscar: `GET /api/organizacoes/?search=hubx`
- Inativar: `PATCH /api/organizacoes/<id>/inativar/`
- Exportar histórico: `GET /api/organizacoes/<id>/history/?export=csv`

### Perguntas frequentes
- **Posso alterar o slug manualmente?** Sim, mas o sistema ajusta automaticamente para garantir unicidade.
- **O que acontece ao excluir uma organização?** O registro é apenas marcado como deletado e pode ser auditado depois.
- **Como adicionar usuários a uma organização?** A vinculação é feita no módulo de contas; este app apenas exibe as associações.
- **Receberei e‑mails sempre que editar uma organização?** Sim, membros cadastrados são notificados sobre criações, alterações, inativações, reativações e exclusões.

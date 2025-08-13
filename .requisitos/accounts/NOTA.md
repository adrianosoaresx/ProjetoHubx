# Descrição do App **Accounts**

## Visão geral

O app **Accounts** é responsável por todo o ciclo de vida das contas de usuário no Hubx.  Ele oferece desde o cadastro inicial (com etapas de validação de CPF e convite) até a edição completa do perfil, autenticação, recuperação de senha e exclusão de contas.  O app também inclui funcionalidades avançadas como **limite de tentativas de login**, **autenticação em duas etapas (2FA)**, **gestão de conexões sociais**, **upload de mídias** e **registro de eventos de segurança**.

Todos os modelos do app herdam `TimeStampedModel` e `SoftDeleteModel`, garantindo campos automáticos de criação/modificação e permitindo exclusões lógicas.  O modelo `User` personalizado usa o **e‑mail como identificador principal**, inclui campos adicionais (CPF, redes sociais, biografia, foto de capa, avatar) e propriedades para diferenciar tipos de usuário (root, admin, coordenador, nucleado, associado e convidado).  Ele armazena contadores de tentativas de login e suporte a 2FA, além de campos para controle de bloqueio de conta e confirmação de e‑mail【663883516891040†L161-L167】.

## Funcionalidades principais

### Cadastro de usuário

- **Fluxo multietapas**: o usuário passa por telas separadas para informar nome completo, CPF, endereço de e‑mail, nome de usuário, senha e foto de perfil.  Após aceitar os termos, o cadastro é finalizado.  Esse fluxo é iniciado a partir de um token de convite (`TokenAcesso`), que determina o tipo de usuário (admin, coordenador, nucleado, associado ou convidado) e pode vincular o novo usuário a um núcleo de organização【468452489923779†L509-L549】.
- **Validação de e‑mail e CPF**: `CustomUserCreationForm` rejeita e‑mails já utilizados e valida CPF com 11 dígitos; ao salvar, a conta é criada inativa e é gerado um token de confirmação que expira em 24 horas【975859753574672†L59-L73】.
- **Confirmação de e‑mail**: ao receber o token de confirmação via e‑mail, o endpoint `confirmar_email` verifica se o token está válido e, caso positivo, ativa o usuário e marca o e‑mail como confirmado【468452489923779†L374-L399】.  Existe também um endpoint para reenviar o e‑mail de confirmação com um novo token válido por 24 h【468452489923779†L406-L433】.

### Autenticação e recuperação de senha

- **Login via e‑mail**: o backend customizado `EmailBackend` autentica usuários usando o e‑mail.  A cada tentativa, ele registra um `LoginAttempt` com e‑mail e endereço IP.  Em caso de três tentativas falhas consecutivas, o usuário é bloqueado por 15 minutos, atualizando `lock_expires_at` e `failed_login_attempts`【499093782196605†L38-L42】.  Tentativas bem‑sucedidas resetam o contador de falhas【499093782196605†L33-L36】.
- **Autenticação em duas etapas (2FA)**: usuários podem ativar 2FA com códigos TOTP.  Na ativação, um segredo é gerado e apresentado em forma de QR code; ao inserir um código válido, o campo `two_factor_enabled` é marcado como `True` e o segredo é gravado【468452489923779†L110-L150】.  Para desativar, um código TOTP também é exigido.  Durante o login, se 2FA estiver habilitado, o formulário de login exige o código TOTP além da senha【975859753574672†L252-L257】.
- **Recuperação de senha**: a view `password_reset` gera um token de redefinição válido por uma hora e envia e‑mail assíncrono com o link.  A view `password_reset_confirm` valida o token, permite ao usuário definir nova senha e reseta os contadores de tentativas de login【468452489923779†L315-L363】.  O `AccountViewSet` fornece endpoints REST para solicitar e confirmar a recuperação de senha【305308945307141†L61-L98】.

### Edição de perfil e redes sociais

- **Informações pessoais**: usuários autenticados podem atualizar nome, e‑mail, CPF, avatar, foto de capa, biografia e contatos.  Se o e‑mail for alterado, a conta é novamente marcada como inativa e um novo token de confirmação é enviado【975859753574672†L134-L159】.
- **Redes sociais**: o formulário `RedesSociaisForm` permite armazenar links de redes sociais em JSON, com validação de formato.  As redes podem ser editadas independentemente das informações pessoais【975859753574672†L162-L177】.
- **Segurança**: página específica permite alterar a senha atual (com validação) e apresenta opções de ativação/desativação da autenticação em duas etapas【468452489923779†L84-L150】.

### Conexões sociais

- Usuários podem manter **conexões** com outros usuários, semelhantes a “amizades”.  O modelo `User` possui relacionamentos `connections` (muitos‑para‑muitos) e `followers` para acompanhar quem segue quem【663883516891040†L227-L235】.  Na interface de perfil, é possível listar as conexões atuais e remover uma conexão existente【468452489923779†L180-L188】.  A funcionalidade de adicionar conexões é prevista para ser implementada futuramente.

### Gerenciamento de mídias

- **Upload de arquivos**: o app permite que usuários enviem arquivos de mídia (imagens, vídeos, PDFs) através de `UserMedia`.  O formulário `MediaForm` suporta adição de tags em texto livre, separadas por vírgulas【975859753574672†L187-L217】.  No `save`, são criados/recuperados objetos `MediaTag` para cada tag e associados à mídia【975859753574672†L202-L218】.
- **Validações**: a classe `UserMedia.clean` verifica se a extensão do arquivo está em uma lista permitida (`USER_MEDIA_ALLOWED_EXTS`) e se o tamanho não ultrapassa o limite (`USER_MEDIA_MAX_SIZE`), retornando erro caso contrário【663883516891040†L289-L300】.
- **Visualização e edição**: há views para listar mídias do usuário com filtro por descrição ou tags, visualizar detalhes, editar descrição/tags e excluir arquivos【468452489923779†L190-L252】.

### Exclusão de conta e purga de dados

- Usuários podem solicitar a exclusão de sua conta.  A view `excluir_conta` exige uma confirmação textual (“EXCLUIR”), marca a conta como `deleted` e `is_active=False` e grava um evento de segurança.  Após a exclusão lógica, o usuário é desconectado【468452489923779†L274-L296】.
- Um task periódico `purge_soft_deleted` remove definitivamente contas que estão marcadas como `deleted` há mais de 30 dias e cuja exclusão foi confirmada【732672362436324†L37-L42】.  Antes desse prazo, a exclusão pode ser cancelada via API (`cancel_delete`)【305308945307141†L151-L158】.

### API REST

O arquivo `accounts/api.py` define um `AccountViewSet` com endpoints REST úteis para clientes (por exemplo, aplicativos móveis).  Os principais pontos são:

- **/confirm‑email**: confirma e‑mail via token【305308945307141†L28-L45】.
- **/resend‑confirmation**: reenviar e‑mail de confirmação para contas ainda não ativadas【305308945307141†L47-L58】.
- **/request‑password‑reset** e **/reset‑password**: solicitar e redefinir senha【305308945307141†L61-L98】.
- **/enable‑2fa** e **/disable‑2fa**: ativar/desativar 2FA via API, retornando o QR code/secret quando necessário【305308945307141†L100-L124】.
- **/me** (DELETE) e **/me/cancel‑delete**: realizar exclusão lógica da própria conta ou cancelar um processo de exclusão pendente【305308945307141†L138-L163】.

### Auditoria e eventos de segurança

- Cada tentativa de login gera um registro `LoginAttempt` com indicador de sucesso/fracasso e IP de origem【499093782196605†L21-L41】.
- Ações sensíveis (confirmação de e‑mail, redefinição de senha, ativação/desativação de 2FA, exclusão de conta, alteração de senha) criam registros em `SecurityEvent`, armazenando data/hora, usuário e IP【305308945307141†L119-L123】【468452489923779†L387-L399】.  Esses registros permitem auditoria e detecção de abusos.

## Fluxos principais (casos de uso)

| Código | Descrição resumida | Passos principais |
|-------|-------------------|------------------|
| **UC‑01** | Criar conta (onboarding) | Usuário inicia cadastro via token de convite, informa nome completo, CPF, e‑mail e senha, adiciona foto e aceita termos; sistema cria conta inativa, envia e‑mail de confirmação e aguarda ativação. |
| **UC‑02** | Confirmar e‑mail | Usuário clica no link enviado no e‑mail de confirmação; se o token estiver válido (<24h), a conta é ativada e marcada como confirmada. Caso contrário, é exibida mensagem de erro e o usuário pode solicitar novo envio. |
| **UC‑03** | Login | Usuário fornece e‑mail, senha (e código TOTP se 2FA estiver habilitado). Se as credenciais estiverem corretas e a conta estiver ativa, é autenticado; três falhas consecutivas resultam em bloqueio de 15 minutos. |
| **UC‑04** | Recuperar senha | Usuário solicita redefinição informando e‑mail; sistema gera token de 1 h e envia e‑mail. Ao clicar no link, o usuário insere nova senha, resetando contadores de login. |
| **UC‑05** | Editar perfil | Usuário autenticado acessa a área de perfil, altera dados pessoais (nome, CPF, e‑mail, biografia, avatar, capa), contatos e redes sociais. Alteração de e‑mail torna a conta inativa até nova confirmação. |
| **UC‑06** | Ativar/Desativar 2FA | Usuário solicita QR code para configurar 2FA, escaneia no aplicativo e informa código TOTP para ativar. Para desativar, fornece novo código TOTP de confirmação. |
| **UC‑07** | Gerenciar mídias | Usuário faz upload de arquivos, adiciona descrição e tags, lista e pesquisa mídias, edita ou remove arquivos. |
| **UC‑08** | Excluir conta | Usuário informa confirmação textual para excluir; sistema marca conta como deletada, registra evento e desconecta. O usuário pode cancelar dentro de 30 dias via API. |

## Observações relevantes

- O app utiliza **Celery** para envio assíncrono de e‑mails de confirmação e redefinição de senha【732672362436324†L24-L34】.
- Campos como `cpf`, `biografia`, `cover`, `avatar`, `redes_sociais` e `perfil_publico` permitem personalizar perfis além do mínimo obrigatório.
- O app integra com outros módulos (tokens, núcleos, organizações) para determinar permissões iniciais e vínculos de usuários.

## Comparação requisitos × implementação

### Requisitos existentes implementados

1. **Cadastro de usuário com e‑mail único e senha** – implementado através do formulário de criação de usuário, com verificação de unicidade de e‑mail e CPF【975859753574672†L59-L73】.  O cadastro, no entanto, é mais completo que o requisito, pois inclui fluxo multietapas e dados adicionais.
2. **Autenticação (login/logout)** – presente via `EmailBackend` e views de login/logout; login utiliza e‑mail, permite autenticação com 2FA e controla sessão.
3. **Recuperação de senha via e‑mail com token expirável em 1 h** – implementado com criação de token e envio de e‑mail assíncrono; o token expira em uma hora【468452489923779†L315-L363】.
4. **Edição de perfil (nome, CPF, e‑mail, avatar, capa, biografia e contatos)** – implementado via `InformacoesPessoaisForm`, `RedesSociaisForm` e views de perfil【975859753574672†L134-L159】.
5. **Validação de e‑mail único globalmente** – implementado no formulário de criação de usuário, que dispara erro para e‑mails já cadastrados【975859753574672†L35-L39】.
6. **Tokens com entropia ≥ 128 bits e expiração de 24 h** – tokens gerados por `generate_secure_token` (entropia alta) e campos `expires_at` na criação de `AccountToken`【663883516891040†L161-L167】.
7. **Limite de 3 tentativas de login com bloqueio de 15 min** – implementado no backend de autenticação, incrementando `failed_login_attempts` e definindo `lock_expires_at`【499093782196605†L38-L42】.
8. **Exclusão de conta via soft delete com purga após 30 dias** – o usuário solicita exclusão, que marca a conta como `deleted`; o task `purge_soft_deleted` remove de forma definitiva após 30 dias【732672362436324†L37-L42】.  Há opção de cancelar a exclusão via API.
9. **Autenticação em duas etapas opcional (2FA)** – implementada com pyotp; usuário pode habilitar/desabilitar, e login exige código TOTP quando habilitado【468452489923779†L110-L150】.
10. **Logs de tentativas de login e eventos de segurança com data/hora e IP** – modelado por `LoginAttempt` e `SecurityEvent`, populados durante autenticação e ações sensíveis【499093782196605†L21-L41】.

### Funcionalidades implementadas não contempladas nos requisitos originais

1. **Fluxo de registro multietapas com convite** – cadastro orientado por token de convite, coleta nome completo, CPF, nome de usuário e foto; define tipo de usuário e núcleo automaticamente【468452489923779†L509-L549】.
2. **Gestão de conexões sociais** – usuários podem visualizar conexões e remover vínculos; os modelos `connections` e `followers` permitem implementar rede social【663883516891040†L227-L235】.
3. **Upload e gerenciamento de mídias com tags** – envio de arquivos, classificação com tags, edição e exclusão.  Valida tipo e tamanho dos arquivos【663883516891040†L289-L300】.
4. **Armazenamento de redes sociais em JSON** – formulário específico (`RedesSociaisForm`) para cadastrar links de redes sociais em formato JSON【975859753574672†L162-L177】.
5. **Registro de eventos de segurança detalhados** – criação de registros para ações como alteração de senha, ativação/desativação de 2FA, confirmação de e‑mail e exclusão de conta【305308945307141†L119-L123】【468452489923779†L387-L399】.
6. **API REST para contas** – endpoints para confirmar e-mail, solicitar/redefinir senha, gerenciar 2FA, excluir conta e cancelar exclusão【305308945307141†L28-L45】【305308945307141†L138-L163】.

Essas funcionalidades não estão documentadas no arquivo de requisitos original e devem ser adicionadas para refletir o escopo real do app.


Hubx
====
Projeto Django que conecta comunidades e empresas. Agora inclui modelos de perfil
e configurações de notificação, além de um script para gerar o SQL de criação das
tabelas.

Após concluir o cadastro de um novo usuário, ele é autenticado automaticamente e
redirecionado para sua página de perfil.

O fluxo de autenticação utiliza agora os formulários padrões do Django. Para registrar-se, acesse `/accounts/onboarding/`.

Configuração inicial
--------------------
Antes de executar ``generate_test_data``, instale as dependências e aplique
as migrações do banco de dados. A execução de ``python manage.py migrate``
cria o usuário padrão ``root`` necessário para o comando:

```
pip install -r requirements.txt
python manage.py migrate
```

### Erro "No module named 'channels'"

Se ao executar ``python manage.py check`` for exibido o erro acima, verifique se
as dependências foram instaladas corretamente com ``pip install -r
requirements.txt``. O pacote ``channels`` faz parte dos requisitos do projeto e
deve estar presente no ambiente virtual.

Gerar dados de teste
--------------------
Utilize o comando ``generate_test_data`` para popular o banco com
usuários, organizações, núcleos, empresas e eventos de exemplo.
É possível exportar para JSON ou CSV.

```
python manage.py generate_test_data --format json > seed.json
```

### Fórum
O módulo `forum` permite a criação de tópicos e respostas por usuários autenticados. Acesse `/forum/` para visualizar as categorias.

### Chat
O módulo de chat registra cada mensagem enviada entre usuários no banco de dados
(`Mensagem`). Ao abrir uma conversa, as últimas 20 mensagens trocadas são
carregadas para que o histórico fique disponível mesmo após fechar a janela.
Para que o WebSocket do chat funcione corretamente, instale também a
dependência `daphne` indicada em `requirements.txt`.
Ao executar o projeto localmente use `daphne Hubx.asgi:application` em vez do
`runserver` padrão para habilitar conexões WebSocket.

Hubx
====

Projeto Django que conecta comunidades e empresas. Agora inclui modelos de perfil
e configurações de notificação, além de um script para gerar o SQL de criação das
tabelas.

Para garantir que o banco de dados possua todas as tabelas necessárias, execute:

```bash
python scriptDB.py
```

Esse script verifica as tabelas existentes e aplica as migrações faltantes.

Para gerar o arquivo `schema.sql` com as instruções de criação das tabelas, execute:

```bash
python scripts/generate_schema.py
```

O resultado será salvo no arquivo `schema.sql` no diretório raiz.

Após concluir o cadastro de um novo usuário, ele é autenticado automaticamente e
redirecionado para sua página de perfil.

O fluxo de autenticação utiliza agora os formulários padrões do Django. Para registrar-se, acesse `/custom_auth/register/`.

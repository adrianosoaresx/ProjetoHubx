Hubx
====
Projeto Django que conecta comunidades e empresas. Agora inclui modelos de perfil
e configurações de notificação, além de um script para gerar o SQL de criação das
tabelas.

Após concluir o cadastro de um novo usuário, ele é autenticado automaticamente e
redirecionado para sua página de perfil.

O fluxo de autenticação utiliza agora os formulários padrões do Django. Para registrar-se, acesse `/accounts/onboarding/`.

Gerar dados de teste
--------------------
Utilize o comando ``generate_test_data`` para popular o banco com
usuários, organizações, núcleos, empresas e eventos de exemplo.
É possível exportar para JSON ou CSV.

```
python manage.py generate_test_data --format json > seed.json
```

Todos os usuários gerados utilizam a senha padrão ``J0529*4351``.


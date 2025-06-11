Hubx
====

Projeto Django que conecta comunidades e empresas. Agora inclui modelos de perfil
e configurações de notificação, além de um script para gerar o SQL de criação das
tabelas.

Para gerar o arquivo `schema.sql` com as instruções de criação das tabelas, execute:

```bash
python scripts/generate_schema.py
```

O resultado será salvo no arquivo `schema.sql` no diretório raiz.

# Infra

## Celery Beat - Feed Plugins

A execução periódica dos plugins do feed é realizada pela tarefa
`feed.tasks.executar_plugins`, agendada no `celery beat` pela entrada
`executar_feed_plugins`.

O intervalo padrão é de 1 minuto, mas pode ser personalizado definindo a
variável de ambiente `FEED_PLUGINS_INTERVAL_MINUTES` com o número desejado de
minutos. Exemplo:

```bash
export FEED_PLUGINS_INTERVAL_MINUTES=5
```

Com isso, o `celery beat` chamará `feed.tasks.executar_plugins` a cada 5
minutos.

## Deploy na Hostinger (build/startup)

Para evitar deploy sem traduções compiladas, use os comandos abaixo no processo de
build/startup da Hostinger:

### Script/Build command

```bash
bash scripts/hostinger_build.sh
```

Esse build garante explicitamente que:

1. as dependências Python foram instaladas;
2. os binários do gettext (`msgfmt`, `msgmerge`, `xgettext`) estão disponíveis;
3. `python manage.py compilemessages` roda **após instalar dependências** e **antes
   de subir a aplicação**;
4. o artefato final contém arquivos `django.mo` em `*/locale/*/LC_MESSAGES/django.mo`.

### Startup command

```bash
bash scripts/hostinger_start.sh
```

## Traduções: regra operacional

Sempre que houver alteração em arquivos `.po`, é obrigatório recompilar as
traduções (`python manage.py compilemessages`) antes do deploy, para garantir a
presença dos `.mo` no artefato publicado.

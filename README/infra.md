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

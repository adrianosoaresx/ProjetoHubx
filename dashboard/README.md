# Dashboard

Este app fornece visualizações de métricas com parâmetros flexíveis e suporte a exportação.

## Parâmetros

A view base aceita os seguintes parâmetros via query string:

- `periodo`: `mensal`, `trimestral`, `semestral`, `anual`.
- `escopo`: `auto`, `global`, `organizacao`, `nucleo`, `evento`.
- `organizacao_id`, `nucleo_id`, `evento_id`: identificadores para filtragem.
- `metricas`: lista separada por vírgula com métricas desejadas (ex.: `num_users,num_eventos`).

Exemplo:

```
/dashboard/admin/?periodo=anual&escopo=organizacao&organizacao_id=1&metricas=num_users,num_eventos
```

## Exportação de métricas

Usuários root, admin e coordenador podem exportar as métricas atuais:

```
/dashboard/export/?formato=csv
/dashboard/export/?formato=pdf&periodo=mensal&escopo=global
```

O arquivo gerado inclui `total` e `crescimento` de cada métrica.

## Configurações salvas

É possível salvar conjuntos de filtros utilizando `DashboardConfig`:

1. Acesse `/dashboard/configs/create/` com os parâmetros desejados na URL.
2. Preencha o nome e, se for admin/root, marque `publico` para compartilhar.
3. As configurações aparecem em `/dashboard/configs/`.
4. Para aplicar uma configuração, use `/dashboard/configs/<id>/apply/`.

Exemplo de JSON armazenado:

```json
{
  "periodo": "mensal",
  "escopo": "organizacao",
  "filters": {"organizacao_id": 1, "metricas": ["num_users"]}
}
```

O cache das métricas expira em 5 minutos. Para invalidar manualmente, utilize o comando `python manage.py clear_cache` ou limpe o backend configurado.

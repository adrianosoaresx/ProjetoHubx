# Dashboard

Este app fornece visualizações de métricas com parâmetros flexíveis e suporte a exportação.

## PWA e suporte offline

O dashboard pode ser instalado como um aplicativo no navegador. Ao acessar `/dashboard/`,
o navegador oferece a opção de adicionar o Hubx Dashboard à tela inicial. O aplicativo
funciona offline graças ao *service worker*, que armazena em cache os assets estáticos e
as requisições HTMX mais recentes.

1. Visite `/dashboard/` em um navegador compatível.
2. Aceite o prompt de instalação ou utilize a opção "Adicionar à tela inicial".
3. O aplicativo continua acessível mesmo sem conexão de rede.

## Parâmetros

A view base aceita os seguintes parâmetros via query string:

- `periodo`: `mensal`, `trimestral`, `semestral`, `anual`.
- `escopo`: `auto`, `global`, `organizacao`, `nucleo`, `evento`.
- `organizacao_id`, `nucleo_id`, `evento_id`: identificadores para filtragem.
- `metricas`: múltiplos valores permitidos (ex.: `metricas=num_users&metricas=num_eventos`).
- `data_inicio`, `data_fim`: limites opcionais de datas no formato ISO `YYYY-MM-DD`.

Exemplo:

```
/dashboard/admin/?periodo=anual&escopo=organizacao&organizacao_id=1&metricas=num_users&metricas=num_eventos
```

## Métricas disponíveis

- `num_posts_feed_total`: total de posts no feed.
- `num_posts_feed_recent`: posts criados nas últimas 24h.
- `num_topicos`: total de tópicos de discussão.
- `num_respostas`: total de respostas em tópicos.

## Exportação de métricas

Usuários root, admin e coordenador podem exportar as métricas atuais:

```
/dashboard/export/?formato=csv
/dashboard/export/?formato=pdf&periodo=mensal&escopo=global
```

O arquivo gerado inclui `total` e a variação percentual calculada como `(valor_atual - valor_anterior) / max(valor_anterior, 1) * 100`.

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

O cache das métricas expira em 5 minutos e utiliza a chave `dashboard-<escopo>-<json dos filtros>`, permitindo reutilização entre usuários com o mesmo escopo e filtros. Para invalidar manualmente, utilize o comando `python manage.py clear_cache` ou limpe o backend configurado.

## Modelos e persistência

Os modelos deste app utilizam os mixins `TimeStampedModel` e `SoftDeleteModel`.

- `TimeStampedModel` fornece os campos automáticos `created` e `modified`.
- `SoftDeleteModel` adiciona remoção lógica via `deleted` e `deleted_at`.

O manager padrão (`objects`) retorna apenas registros não deletados. Para acessar
todos os registros, inclusive os excluídos logicamente, utilize
`Model.all_objects`. Isso é útil em interfaces administrativas ou para
recuperação manual de dados.

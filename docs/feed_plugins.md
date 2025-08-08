# Feed Plugins

O sistema de plugins permite que cada organização injete conteúdo customizado no
feed. Um plugin é uma classe Python que implementa o protocolo
`FeedPlugin` definido em `feed.domain.plugins`.

```python
from feed.domain.plugins import FeedPlugin, CustomItem

class AvisoPlugin:
    def render(self, user):
        return [CustomItem(conteudo="Aviso importante!")]
```

Para ativar um plugin, registre o caminho completo da classe em
`FeedPluginConfig` via painel administrativo.

from feed.domain.plugins import CustomItem


class DummyPlugin:
    def render(self, user):  # pragma: no cover - simples
        return [CustomItem(conteudo="ok")]

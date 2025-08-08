from django.contrib.auth import get_user_model

from feed.application.plugins_loader import load_plugins_for
from feed.models import FeedPluginConfig
from organizacoes.factories import OrganizacaoFactory


def test_load_plugins_for(db):
    org = OrganizacaoFactory()
    FeedPluginConfig.objects.create(
        organizacao=org,
        module_path="feed.tests.sample_plugin.DummyPlugin",
        frequency=1,
    )
    plugins = load_plugins_for(org)
    assert len(plugins) == 1
    plugin = plugins[0]
    User = get_user_model()
    user = User.objects.create_user("tester", "t@example.com", "pass")
    items = plugin.render(user)
    assert items[0].conteudo == "ok"

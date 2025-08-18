from django.contrib.auth import get_user_model

from accounts.factories import UserFactory
from feed.application.plugins_loader import load_plugins_for
from feed.models import FeedPluginConfig
from feed.tasks import executar_plugins
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory
import feed.tests.sample_plugin as sample_plugin


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


def test_executar_plugins_task(monkeypatch, db):
    org = OrganizacaoFactory()
    FeedPluginConfig.objects.create(
        organizacao=org,
        module_path="feed.tests.sample_plugin.DummyPlugin",
        frequency=1,
    )
    user = UserFactory(organizacao=org, nucleo_obj=NucleoFactory(organizacao=org))
    called = {}

    def fake_render(self, u):
        called["user"] = u
        return []

    monkeypatch.setattr(sample_plugin.DummyPlugin, "render", fake_render, raising=False)

    executar_plugins()

    assert called["user"] == user

from Hubx.celery import app as celery_app
from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory
from feed.models import FeedPluginConfig
import feed.tests.sample_plugin as sample_plugin


def test_executar_plugins_scheduled(monkeypatch, db, settings):
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

    schedule = settings.CELERY_BEAT_SCHEDULE["executar_feed_plugins"]
    assert schedule["task"] == "feed.tasks.executar_plugins"

    celery_app.tasks[schedule["task"]].apply()

    assert called["user"] == user

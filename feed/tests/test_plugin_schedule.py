from Hubx.celery import app as celery_app
from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory
from feed.models import FeedPluginConfig
from freezegun import freeze_time
from django.utils import timezone
import feed.tests.sample_plugin as sample_plugin


def test_executar_plugins_scheduled(monkeypatch, db, settings):
    org = OrganizacaoFactory()
    config = FeedPluginConfig.objects.create(
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

    with freeze_time("2024-01-01 00:00:00"):
        celery_app.tasks[schedule["task"]].apply()
        config.refresh_from_db()
        assert config.last_run == timezone.now()

    assert called["user"] == user


def test_executar_plugins_periodic(monkeypatch, db):
    """Simula chamadas periódicas do celery beat para os plugins."""

    org = OrganizacaoFactory()
    FeedPluginConfig.objects.create(
        organizacao=org,
        module_path="feed.tests.sample_plugin.DummyPlugin",
        frequency=1,
    )
    user = UserFactory(organizacao=org, nucleo_obj=NucleoFactory(organizacao=org))
    calls: list = []

    def fake_render(self, u):
        calls.append(u)
        return []

    monkeypatch.setattr(sample_plugin.DummyPlugin, "render", fake_render, raising=False)

    task = celery_app.tasks["feed.tasks.executar_plugins"]
    with freeze_time("2024-01-01 00:00:00"):
        task.apply()
    with freeze_time("2024-01-01 00:00:30"):
        task.apply()

    assert calls == [user]

    with freeze_time("2024-01-01 00:01:30"):
        task.apply()

    assert calls == [user, user]

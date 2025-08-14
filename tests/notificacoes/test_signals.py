import pytest
from django.apps import apps
from django.db.models.signals import post_migrate

from notificacoes.models import NotificationTemplate
from notificacoes.services import metrics

pytestmark = pytest.mark.django_db


def test_atualizar_templates_total_atualiza_gauge() -> None:
    before = NotificationTemplate.objects.count()

    NotificationTemplate.objects.create(
        codigo="active",
        assunto="Oi",
        corpo="{{ nome }}",
        canal="email",
    )
    inactive = NotificationTemplate.objects.create(
        codigo="inactive",
        assunto="Oi",
        corpo="{{ nome }}",
        canal="email",
    )
    inactive.delete()

    metrics.templates_total.set(0)
    app_config = apps.get_app_config("notificacoes")
    post_migrate.send(
        sender=app_config,
        app_config=app_config,
        verbosity=0,
        interactive=False,
        using="default",
    )
    assert metrics.templates_total._value.get() == before + 1

    NotificationTemplate.objects.filter(codigo="active").delete()
    post_migrate.send(
        sender=app_config,
        app_config=app_config,
        verbosity=0,
        interactive=False,
        using="default",
    )
    assert metrics.templates_total._value.get() == before

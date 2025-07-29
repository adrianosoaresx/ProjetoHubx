import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationStatus, NotificationTemplate, UserNotificationPreference

pytestmark = pytest.mark.django_db


def test_template_str() -> None:
    template = NotificationTemplate.objects.create(codigo="welcome", assunto="Oi", corpo="{{ nome }}", canal="email")
    assert str(template) == "welcome"


def test_preference_str() -> None:
    user = UserFactory()
    pref = UserNotificationPreference.objects.create(user=user)
    assert f"{user}" in str(pref)


def test_log_str() -> None:
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="x", assunto="x", corpo="x", canal="email")
    log = NotificationLog.objects.create(
        user=user,
        template=template,
        canal="email",
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
    )
    assert template.codigo in str(log)

import pytest

import pytest
from accounts.factories import UserFactory
from notificacoes.models import (
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
    UserNotificationPreference,
)

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
        status=NotificationStatus.PENDENTE,
    )
    assert template.codigo in str(log)


def test_preferencias_criadas_automaticamente() -> None:
    user = UserFactory()
    assert UserNotificationPreference.objects.filter(user=user).exists()


def test_log_nao_pode_ser_deletado():
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="a", assunto="a", corpo="a", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")
    with pytest.raises(PermissionError):
        log.delete()

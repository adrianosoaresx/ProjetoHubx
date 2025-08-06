import pytest

from accounts.factories import UserFactory
from configuracoes.models import ConfiguracaoConta
from notificacoes.models import (
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
)

pytestmark = pytest.mark.django_db


def test_template_str() -> None:
    template = NotificationTemplate.objects.create(codigo="welcome", assunto="Oi", corpo="{{ nome }}", canal="email")
    assert str(template) == "welcome"


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


def test_configuracao_criada_automaticamente() -> None:
    user = UserFactory()
    assert ConfiguracaoConta.objects.filter(user=user).exists()


def test_log_nao_pode_ser_deletado():
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="a", assunto="a", corpo="a", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")
    with pytest.raises(PermissionError):
        log.delete()


def test_log_nao_pode_ser_alterado():
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="b", assunto="b", corpo="b", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")
    log.canal = "push"
    with pytest.raises(PermissionError):
        log.save()


def test_log_permite_atualizar_status():
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="c", assunto="c", corpo="c", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")
    log.status = NotificationStatus.ENVIADA
    log.save()
    log.refresh_from_db()
    assert log.status == NotificationStatus.ENVIADA

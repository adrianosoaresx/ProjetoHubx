import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from notificacoes.models import Canal, NotificationLog, NotificationStatus, NotificationTemplate

pytestmark = pytest.mark.django_db


@pytest.fixture
def template_push():
    return NotificationTemplate.objects.create(
        codigo="tpl-push", assunto="Assunto", corpo="Mensagem", canal=Canal.PUSH
    )


def test_dropdown_lists_only_authenticated_user_notifications(client, template_push):
    user = UserFactory()
    other_user = UserFactory()
    NotificationLog.objects.create(
        user=user,
        template=template_push,
        canal=Canal.PUSH,
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
    )
    NotificationLog.objects.create(
        user=other_user,
        template=template_push,
        canal=Canal.PUSH,
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
    )
    NotificationLog.objects.create(
        user=user,
        template=template_push,
        canal=Canal.PUSH,
        status=NotificationStatus.PENDENTE,
        data_envio=timezone.now(),
    )

    client.force_login(user)
    response = client.get(reverse("notificacoes:notifications-dropdown"))

    content = response.content.decode()
    assert response.status_code == 200
    assert template_push.assunto in content
    assert content.count(template_push.assunto) == 1


def test_dropdown_contains_accessibility_attributes(client, template_push):
    user = UserFactory()
    NotificationLog.objects.create(
        user=user,
        template=template_push,
        canal=Canal.PUSH,
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
    )

    client.force_login(user)
    response = client.get(reverse("notificacoes:notifications-dropdown"))

    html = response.content.decode()
    assert "role=\"menuitem\"" in html
    assert "tabindex=\"0\"" in html
    assert "aria-live=\"polite\"" in html
    assert reverse("notificacoes:notificacoes-list") in html

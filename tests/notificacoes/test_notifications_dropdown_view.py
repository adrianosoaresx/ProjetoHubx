import pytest
import uuid
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from feed.factories import PostFactory
from notificacoes.models import Canal, NotificationLog, NotificationStatus, NotificationTemplate
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def template_push():
    return NotificationTemplate.objects.create(
        codigo="tpl-push", assunto="Assunto", corpo="Mensagem", canal=Canal.PUSH
    )


@pytest.fixture
def template_app():
    return NotificationTemplate.objects.create(
        codigo="tpl-app", assunto="Assunto app", corpo="Mensagem app", canal=Canal.APP
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


def test_dropdown_includes_in_app_notifications(client, template_app):
    user = UserFactory()
    NotificationLog.objects.create(
        user=user,
        template=template_app,
        canal=Canal.APP,
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
    )

    client.force_login(user)
    response = client.get(reverse("notificacoes:notifications-dropdown"))

    content = response.content.decode()
    assert response.status_code == 200
    assert template_app.assunto in content


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


def test_feed_notification_links_to_feed_detail(client):
    organizacao = OrganizacaoFactory()
    user = UserFactory(organizacao=organizacao)
    post = PostFactory(autor=user, organizacao=organizacao)
    template = NotificationTemplate.objects.create(
        codigo=f"feed_test_{uuid.uuid4()}",
        assunto="Novo post",
        corpo="Post criado",
        canal=Canal.APP,
    )
    NotificationLog.objects.create(
        user=user,
        template=template,
        canal=Canal.APP,
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
        context={"post_id": str(post.id)},
    )

    client.force_login(user)
    response = client.get(reverse("notificacoes:notifications-dropdown"))

    expected_url = f"{reverse('feed:post_detail', kwargs={'pk': post.id})}#post-{post.id}"
    assert expected_url in response.content.decode()

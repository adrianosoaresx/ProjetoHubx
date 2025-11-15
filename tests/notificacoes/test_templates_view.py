import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from notificacoes.models import NotificationTemplate


pytestmark = pytest.mark.django_db


def test_toggle_template(client):
    user = UserFactory()
    perm = Permission.objects.get(codename="change_notificationtemplate")
    user.user_permissions.add(perm)
    client.force_login(user)

    template = NotificationTemplate.objects.create(
        codigo="t1", assunto="a", corpo="b", canal="email", ativo=True
    )

    url = reverse("notificacoes:template_toggle", args=[template.codigo])
    response = client.post(url)
    assert response.status_code == 302
    template.refresh_from_db()
    assert template.ativo is False

    response = client.post(url)
    template.refresh_from_db()
    assert template.ativo is True


def test_admin_can_toggle_without_explicit_permission(client):
    user = UserFactory(user_type=UserType.ADMIN.value, is_staff=True)
    user.save(update_fields=["user_type", "is_staff"])
    client.force_login(user)

    template = NotificationTemplate.objects.create(
        codigo="tpl-admin", assunto="a", corpo="b", canal="email", ativo=True
    )

    url = reverse("notificacoes:template_toggle", args=[template.codigo])
    response = client.post(url)
    assert response.status_code == 302
    template.refresh_from_db()
    assert template.ativo is False


def test_delete_template_requires_post(client):
    user = UserFactory()
    perm = Permission.objects.get(codename="delete_notificationtemplate")
    user.user_permissions.add(perm)
    client.force_login(user)

    template = NotificationTemplate.objects.create(
        codigo="del", assunto="a", corpo="b", canal="email", ativo=True
    )

    url = reverse("notificacoes:template_delete", args=[template.codigo])
    response = client.get(url)
    assert response.status_code == 200
    assert NotificationTemplate.objects.filter(pk=template.pk).exists()

    response = client.post(url)
    assert response.status_code == 302
    assert not NotificationTemplate.objects.filter(pk=template.pk).exists()


def test_admin_can_delete_without_explicit_permission(client):
    user = UserFactory(user_type=UserType.ADMIN.value, is_staff=True)
    user.save(update_fields=["user_type", "is_staff"])
    client.force_login(user)

    template = NotificationTemplate.objects.create(
        codigo="del-admin", assunto="a", corpo="b", canal="email", ativo=True
    )

    url = reverse("notificacoes:template_delete", args=[template.codigo])
    response = client.post(url)

    assert response.status_code == 302
    assert not NotificationTemplate.objects.filter(pk=template.pk).exists()


def test_edit_template_codigo_unchanged(client):
    user = UserFactory()
    perm = Permission.objects.get(codename="change_notificationtemplate")

    user.user_permissions.add(perm)
    client.force_login(user)

    template = NotificationTemplate.objects.create(
        codigo="orig", assunto="a", corpo="b", canal="email", ativo=True
    )

    url = reverse("notificacoes:template_edit", args=[template.codigo])
    response = client.post(
        url,
        {
            "codigo": "novo",
            "assunto": "novo assunto",
            "corpo": "novo corpo",
            "canal": "email",
            "ativo": "on",
        },
    )

    assert response.status_code == 302
    template.refresh_from_db()
    assert template.codigo == "orig"
    assert template.assunto == "novo assunto"


def _grant_permission(user, codename: str) -> None:
    perm = Permission.objects.get(codename=codename)
    user.user_permissions.add(perm)


@pytest.mark.parametrize(
    "referer",
    [
        "/configuracoes/?panel=notificacoes&notification_templates_page=2#notificacoes",
        None,
    ],
)
def test_create_template_cancel_component_uses_back_href(client, referer):
    user = UserFactory()
    _grant_permission(user, "add_notificationtemplate")
    client.force_login(user)

    url = reverse("notificacoes:template_create")
    request_kwargs = {}
    if referer:
        request_kwargs["HTTP_REFERER"] = referer

    response = client.get(url, **request_kwargs)

    assert response.status_code == 200

    expected_fallback = (
        f"{reverse('configuracoes:configuracoes')}?panel=notificacoes#notificacoes"
    )

    cancel_config = response.context["cancel_component_config"]
    expected_href = referer or expected_fallback

    assert cancel_config["href"] == expected_href
    assert cancel_config["fallback_href"] == expected_fallback
    assert cancel_config.get("prevent_history") is True


@pytest.mark.parametrize(
    "referer",
    [
        "/configuracoes/?panel=notificacoes&notification_templates_page=2#notificacoes",
        None,
    ],
)
def test_edit_template_cancel_component_uses_back_href(client, referer):
    user = UserFactory()
    _grant_permission(user, "change_notificationtemplate")
    client.force_login(user)

    template = NotificationTemplate.objects.create(
        codigo="edit-cancel",
        assunto="a",
        corpo="b",
        canal="email",
        ativo=True,
    )

    url = reverse("notificacoes:template_edit", args=[template.codigo])
    request_kwargs = {}
    if referer:
        request_kwargs["HTTP_REFERER"] = referer

    response = client.get(url, **request_kwargs)

    assert response.status_code == 200

    expected_fallback = (
        f"{reverse('configuracoes:configuracoes')}?panel=notificacoes#notificacoes"
    )

    cancel_config = response.context["cancel_component_config"]
    expected_href = referer or expected_fallback

    assert cancel_config["href"] == expected_href
    assert cancel_config["fallback_href"] == expected_fallback
    assert cancel_config.get("prevent_history") is True

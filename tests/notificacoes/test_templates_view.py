import re

import pytest
from django.contrib.auth.models import Permission
from django.test import override_settings
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
    "referer, expected_href",
    [
        (
            "/configuracoes/?panel=notificacoes&notification_templates_page=2#notificacoes",
            "/configuracoes/?panel=notificacoes&notification_templates_page=2#notificacoes",
        ),
        ("/notificacoes/templates/", None),
        (None, None),
    ],
)
def test_create_template_back_href_prioritizes_notifications_panel(client, referer, expected_href):
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

    assert response.context["back_href"] == (expected_href or expected_fallback)


@pytest.mark.parametrize(
    "referer, expected_href",
    [
        (
            "/configuracoes/?panel=notificacoes&notification_templates_page=2#notificacoes",
            "/configuracoes/?panel=notificacoes&notification_templates_page=2#notificacoes",
        ),
        ("/notificacoes/templates/", None),
        (None, None),
    ],
)
def test_edit_template_back_href_prioritizes_notifications_panel(client, referer, expected_href):
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

    assert response.context["back_href"] == (expected_href or expected_fallback)


def test_create_template_back_href_ignores_self_referer(client):
    user = UserFactory()
    _grant_permission(user, "add_notificationtemplate")
    client.force_login(user)

    url = reverse("notificacoes:template_create")
    response = client.get(url, HTTP_REFERER=url)

    assert response.status_code == 200

    expected_fallback = (
        f"{reverse('configuracoes:configuracoes')}?panel=notificacoes#notificacoes"
    )
    assert response.context["back_href"] == expected_fallback


def test_create_template_respects_panel_querystring(client):
    user = UserFactory()
    _grant_permission(user, "add_notificationtemplate")
    client.force_login(user)

    url = reverse("notificacoes:template_create")
    response = client.get(url, {"panel": "painel-personalizado"})

    assert response.status_code == 200

    expected_fallback = (
        f"{reverse('configuracoes:configuracoes')}?panel=painel-personalizado#notificacoes"
    )
    assert response.context["back_href"] == expected_fallback


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_cancel_link_keeps_notifications_panel_open(admin_client):
    url = reverse("notificacoes:template_create")
    response = admin_client.get(url, HTTP_REFERER="/notificacoes/templates/")

    assert response.status_code == 200

    back_href = response.context["back_href"]
    settings_response = admin_client.get(back_href)

    assert settings_response.status_code == 200

    content = settings_response.content.decode()
    match = re.search(r"<details[^>]*id=\"notificacoes\"[^>]*>", content)
    assert match is not None
    assert "open" in match.group(0)

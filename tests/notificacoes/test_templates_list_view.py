import pytest
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.urls import reverse
from unittest.mock import patch

from accounts.factories import UserFactory
from notificacoes.models import NotificationTemplate


pytestmark = pytest.mark.django_db


@pytest.fixture
def user_with_view_permission():
    user = UserFactory()
    perm = Permission.objects.get(codename="view_notificationtemplate")
    user.user_permissions.add(perm)
    return user


def test_list_templates_requires_view_permission(client):
    user = UserFactory()
    client.force_login(user)

    url = reverse("notificacoes:templates_list")

    response = client.get(url)
    assert response.status_code == 403

    perm = Permission.objects.get(codename="view_notificationtemplate")
    user.user_permissions.add(perm)

    initial_count = NotificationTemplate.objects.count()
    with patch("notificacoes.views.render", return_value=HttpResponse("OK")) as mock_render:
        response = client.get(url)

    assert response.status_code == 200
    mock_render.assert_called_once()
    _, _, context = mock_render.call_args[0]
    page_obj = context["page_obj"]
    assert page_obj.paginator.count == initial_count


def test_list_templates_paginates_results(client, user_with_view_permission):
    client.force_login(user_with_view_permission)

    for index in range(25):
        NotificationTemplate.objects.create(
            codigo=f"tpl-{index}",
            assunto="Assunto",
            corpo="Corpo",
            canal="email",
        )

    url = reverse("notificacoes:templates_list")
    with patch("notificacoes.views.render", return_value=HttpResponse("OK")) as mock_render:
        response = client.get(url)

    assert response.status_code == 200
    mock_render.assert_called_once()
    _, _, context = mock_render.call_args[0]
    page_obj = context["page_obj"]
    total_templates = NotificationTemplate.objects.count()
    expected_first_page = min(page_obj.paginator.per_page, total_templates)
    assert len(page_obj) == expected_first_page
    assert page_obj.number == 1
    assert (total_templates > page_obj.paginator.per_page) == page_obj.has_next()
    assert page_obj.paginator.count == total_templates
    assert context["templates_page"] is page_obj


def test_list_templates_second_page(client, user_with_view_permission):
    client.force_login(user_with_view_permission)

    for index in range(25):
        NotificationTemplate.objects.create(
            codigo=f"tpl-{index}",
            assunto="Assunto",
            corpo="Corpo",
            canal="email",
        )

    url = reverse("notificacoes:templates_list")
    with patch("notificacoes.views.render", return_value=HttpResponse("OK")) as mock_render:
        response = client.get(url, {"page": 2})

    assert response.status_code == 200
    mock_render.assert_called_once()
    _, _, context = mock_render.call_args[0]
    page_obj = context["page_obj"]
    total_templates = NotificationTemplate.objects.count()
    remaining = max(total_templates - page_obj.paginator.per_page, 0)
    expected_second_page = min(page_obj.paginator.per_page, remaining)
    assert len(page_obj) == expected_second_page
    assert page_obj.number == 2
    assert page_obj.has_previous()
    assert page_obj.paginator.count == total_templates

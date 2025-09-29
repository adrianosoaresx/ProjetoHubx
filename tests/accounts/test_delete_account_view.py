import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from accounts.models import SecurityEvent, UserType
from organizacoes.factories import OrganizacaoFactory

User = get_user_model()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls")
@freeze_time("2024-01-01 12:00:00")
def test_delete_account_view(client):
    user = User.objects.create_user(email="del@example.com", username="del", password="pw")
    client.force_login(user)
    url = reverse("excluir_conta", urlconf="accounts.urls")
    resp = client.post(url, {"confirm": "EXCLUIR"})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.deleted is True and user.deleted_at is not None
    assert user.exclusao_confirmada
    assert not user.is_active
    assert SecurityEvent.objects.filter(usuario=user, evento="conta_excluida").exists()
    token = user.account_tokens.get(tipo="cancel_delete")
    assert token.expires_at == timezone.now() + timezone.timedelta(days=30)


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls")
def test_cancel_delete_view_reactivates_user(client):
    user = User.objects.create_user(email="view_cancel@example.com", username="view_cancel", password="pw")
    client.force_login(user)
    client.post(reverse("excluir_conta", urlconf="accounts.urls"), {"confirm": "EXCLUIR"})
    token = user.account_tokens.get(tipo="cancel_delete")
    resp = client.get(reverse("cancel_delete", args=[token.codigo], urlconf="accounts.urls"))
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
    assert not user.deleted and user.deleted_at is None
    assert not user.exclusao_confirmada


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls")
@freeze_time("2024-01-01 12:00:00")
def test_admin_can_delete_other_user_account(client):
    organizacao = OrganizacaoFactory()
    admin = User.objects.create_user(
        email="admin@example.com",
        username="admin",
        password="pw",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
        is_staff=True,
    )
    target = User.objects.create_user(
        email="target@example.com",
        username="target",
        password="pw",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
    )

    client.force_login(admin)
    url = reverse("excluir_conta", urlconf="accounts.urls")
    resp = client.post(
        url,
        {"confirm": "EXCLUIR", "public_id": str(target.public_id), "username": target.username},
    )

    assert resp.status_code == 302
    assert resp.url == reverse("accounts:associados_lista", urlconf="tests.urls")
    target.refresh_from_db()
    assert target.deleted is True and target.deleted_at is not None
    assert not target.is_active
    assert SecurityEvent.objects.filter(usuario=target, evento="conta_excluida").exists()
    token = target.account_tokens.get(tipo="cancel_delete")
    assert token.expires_at == timezone.now() + timezone.timedelta(days=30)


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls")
@freeze_time("2024-01-01 12:00:00")
def test_operator_can_delete_other_user_account(client):
    organizacao = OrganizacaoFactory()
    operator = User.objects.create_user(
        email="operator@example.com",
        username="operator",
        password="pw",
        user_type=UserType.OPERADOR,
        organizacao=organizacao,
    )
    target = User.objects.create_user(
        email="member@example.com",
        username="member",
        password="pw",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
    )

    client.force_login(operator)
    url = reverse("excluir_conta", urlconf="accounts.urls")
    resp = client.post(
        url,
        {"confirm": "EXCLUIR", "public_id": str(target.public_id), "username": target.username},
    )

    assert resp.status_code == 302
    assert resp.url == reverse("accounts:associados_lista", urlconf="tests.urls")
    target.refresh_from_db()
    assert target.deleted
    assert SecurityEvent.objects.filter(usuario=target, evento="conta_excluida").exists()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls")
def test_operator_cannot_delete_user_from_another_organization(client):
    org_a = OrganizacaoFactory()
    org_b = OrganizacaoFactory()
    operator = User.objects.create_user(
        email="operator@example.com",
        username="operator",
        password="pw",
        user_type=UserType.OPERADOR,
        organizacao=org_a,
    )
    outsider = User.objects.create_user(
        email="outsider@example.com",
        username="outsider",
        password="pw",
        user_type=UserType.ASSOCIADO,
        organizacao=org_b,
        is_associado=True,
    )

    client.force_login(operator)
    url = reverse("excluir_conta", urlconf="accounts.urls")
    resp = client.get(url, {"public_id": str(outsider.public_id)})

    assert resp.status_code == 403

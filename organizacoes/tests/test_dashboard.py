from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from validate_docbr import CNPJ

from accounts.models import UserType
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


User = get_user_model()


def _create_org(name: str, slug: str) -> Organizacao:
    generator = CNPJ()
    return Organizacao.objects.create(
        nome=name,
        cnpj=generator.generate(mask=True),
        slug=slug,
    )


def _create_user(email: str, username: str, user_type: UserType, organizacao: Organizacao | None = None):
    return User.objects.create_user(
        email=email,
        username=username,
        password="senha-super-segura",
        user_type=user_type,
        organizacao=organizacao,
    )


@pytest.fixture
def organizacao():
    return _create_org("Organização Central", "organizacao-central")


def test_dashboard_disponivel_para_admin(client, organizacao):
    admin = _create_user(
        "admin@example.com",
        "admin",
        UserType.ADMIN,
        organizacao,
    )
    client.force_login(admin)

    response = client.get(reverse("organizacoes:dashboard", kwargs={"pk": organizacao.pk}))

    assert response.status_code == 200
    assert response.context["organizacao"] == organizacao


def test_dashboard_disponivel_para_root(client, organizacao):
    root_user = _create_user("root@example.com", "root", UserType.ROOT)
    client.force_login(root_user)

    response = client.get(reverse("organizacoes:dashboard", kwargs={"pk": organizacao.pk}))

    assert response.status_code == 200


def test_dashboard_bloqueado_para_associado(client, organizacao):
    associado = _create_user(
        "assoc@example.com",
        "assoc",
        UserType.ASSOCIADO,
        organizacao,
    )
    client.force_login(associado)

    response = client.get(reverse("organizacoes:dashboard", kwargs={"pk": organizacao.pk}))

    assert response.status_code == 403


def test_dashboard_admin_de_outra_org_recebe_404(client, organizacao):
    outra_org = _create_org("Outra Organização", "outra-organizacao")
    admin_outra_org = _create_user(
        "admin2@example.com",
        "admin2",
        UserType.ADMIN,
        outra_org,
    )
    client.force_login(admin_outra_org)

    response = client.get(reverse("organizacoes:dashboard", kwargs={"pk": organizacao.pk}))

    assert response.status_code == 404

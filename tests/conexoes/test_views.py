import os

import django
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from accounts.models import UserType  # noqa: E402
from nucleos.models import Nucleo, ParticipacaoNucleo  # noqa: E402
from organizacoes.models import Organizacao  # noqa: E402


def _create_organizacao() -> Organizacao:
    return Organizacao.objects.create(nome="Org Hubx", cnpj="12345678000195")


def _create_user(*, username: str, email: str, organizacao: Organizacao):
    User = get_user_model()
    return User.objects.create_user(
        username=username,
        email=email,
        password="senha123",
        contato=username.title(),
        user_type=UserType.ASSOCIADO,
        is_associado=True,
        organizacao=organizacao,
    )


@pytest.mark.django_db
def test_perfil_conexoes_renderiza_cards_e_badges_de_nucleo_ativo() -> None:
    organizacao = _create_organizacao()
    solicitante = _create_user(
        username="solicitante",
        email="solicitante@example.com",
        organizacao=organizacao,
    )
    conexao = _create_user(
        username="conexao",
        email="conexao@example.com",
        organizacao=organizacao,
    )

    nucleo = Nucleo.objects.create(organizacao=organizacao, nome="Núcleo Vendas")
    ParticipacaoNucleo.objects.create(
        user=conexao,
        nucleo=nucleo,
        papel="membro",
        status="ativo",
        status_suspensao=False,
    )

    solicitante.connections.add(conexao)

    client = Client()
    client.force_login(solicitante)

    response = client.get(reverse("conexoes:perfil_sections_conexoes"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "connection-card" in content
    assert "Nucleado" in content
    assert "Núcleo Vendas" in content

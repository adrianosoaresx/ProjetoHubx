import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from eventos.factories import EventoFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
def test_list_view_returns_counts(client, admin_user):
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    user = UserFactory(organizacao=org, nucleo_obj=nucleo)
    NucleoFactory(organizacao=org)
    for _ in range(3):
        EventoFactory(organizacao=org, nucleo=nucleo, coordenador=user)

    client.force_login(admin_user)
    response = client.get(reverse("organizacoes:list"))
    obj = response.context["object_list"][0]

    assert obj.users_count == 1
    assert obj.nucleos_count == 2
    assert obj.events_count == 3


@pytest.mark.django_db
def test_list_template_renders_cards(client, admin_user):
    OrganizacaoFactory()
    client.force_login(admin_user)
    response = client.get(reverse("organizacoes:list"))

    content = response.content.decode()
    assert "<table" not in content
    assert "grid gap-6" in content
    assert "Usuários" in content
    assert "Núcleos" in content
    assert "Eventos" in content


@pytest.mark.django_db
def test_list_template_root_hides_counts_and_actions(client):
    OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ROOT)
    client.force_login(user)
    response = client.get(reverse("organizacoes:list"))
    content = response.content.decode()

    assert "Usuários" not in content
    assert "Núcleos" not in content
    assert "Eventos" not in content
    assert "Remover" not in content
    assert "Inativar" not in content
    assert "Reativar" not in content

import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from agenda.factories import EventoFactory
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


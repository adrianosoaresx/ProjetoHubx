import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from agenda.factories import EventoFactory
from empresas.factories import EmpresaFactory
from organizacoes.factories import OrganizacaoFactory


@pytest.fixture
def root_user(django_user_model):
    return django_user_model.objects.create_superuser(
        username="root",
        email="root@example.com",
        password="password",
    )


@pytest.mark.django_db
def test_root_view_shows_summary_cards(client, root_user):
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    user = UserFactory(organizacao=org, nucleo_obj=nucleo)
    for _ in range(2):
        EventoFactory(organizacao=org, nucleo=nucleo, coordenador=user)
    EmpresaFactory(organizacao=org, usuario=user)

    client.force_login(root_user)
    response = client.get(reverse("organizacoes:detail", args=[org.id]))
    content = response.content.decode()

    assert 'id="org-stats"' in content
    assert "Usuários" in content
    assert "Núcleos" in content
    assert "Eventos" in content
    assert "Empresas" in content
    assert len(response.context["usuarios"]) == 1
    assert len(response.context["nucleos"]) == 1
    assert len(response.context["eventos"]) == 2
    assert len(response.context["empresas"]) == 1

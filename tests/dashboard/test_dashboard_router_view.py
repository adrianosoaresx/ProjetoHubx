import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", [UserType.ADMIN, UserType.OPERADOR])
def test_dashboard_router_renders_admin_dashboard_for_management_roles(client, user_type):
    organizacao = OrganizacaoFactory()
    user = UserFactory(user_type=user_type, organizacao=organizacao)

    client.force_login(user)
    response = client.get(reverse("dashboard:admin_dashboard"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert "dashboard/admin_dashboard.html" in template_names

    page = response.content.decode()
    assert "Dashboard administrativo" in page
    assert "Membros" in page
    assert "Nucleados" in page
    assert "Eventos ativos" in page


@pytest.mark.django_db
def test_dashboard_router_renders_consultor_dashboard(client):
    organizacao = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.CONSULTOR, organizacao=organizacao)

    client.force_login(user)
    response = client.get(reverse("dashboard:admin_dashboard"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert "dashboard/consultor_dashboard.html" in template_names

    page = response.content.decode()
    assert "Dashboard do consultor" in page
    assert "Núcleos acompanhados" in page
    assert "Eventos ativos" in page


@pytest.mark.django_db
def test_dashboard_router_detects_consultor_by_nucleo_assignment(client):
    organizacao = OrganizacaoFactory()
    user = UserFactory(
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=False,
    )
    NucleoFactory(organizacao=organizacao, consultor=user)

    client.force_login(user)
    response = client.get(reverse("dashboard:admin_dashboard"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert "dashboard/consultor_dashboard.html" in template_names

    page = response.content.decode()
    assert "Dashboard do consultor" in page


@pytest.mark.django_db
def test_dashboard_router_renders_membro_dashboard(client):
    organizacao = OrganizacaoFactory()
    user = UserFactory(
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
        nucleo_obj=NucleoFactory(organizacao=organizacao),
    )

    client.force_login(user)
    response = client.get(reverse("dashboard:admin_dashboard"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert "dashboard/membro_dashboard.html" in template_names

    page = response.content.decode()
    assert "Meu dashboard" in page
    assert "Total de conexões" in page
    assert "Postagens publicadas" in page


@pytest.mark.django_db
def test_dashboard_router_renders_coordenador_dashboard(client):
    organizacao = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=organizacao)
    user = UserFactory(
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
        is_coordenador=True,
        nucleo=nucleo,
    )
    ParticipacaoNucleo.objects.create(
        user=user,
        nucleo=nucleo,
        papel="coordenador",
        papel_coordenador=ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL,
        status="ativo",
        status_suspensao=False,
    )

    client.force_login(user)
    response = client.get(reverse("dashboard:admin_dashboard"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert "dashboard/coordenadores_dashboard.html" in template_names

    page = response.content.decode()
    assert "Dashboard do coordenador" in page
    assert "Núcleos coordenados" in page
    assert "Eventos ativos" in page


@pytest.mark.django_db
def test_dashboard_router_detects_coordenador_from_participacao(client):
    organizacao = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=organizacao)
    user = UserFactory(
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=False,
        is_coordenador=False,
    )
    ParticipacaoNucleo.objects.create(
        user=user,
        nucleo=nucleo,
        papel="coordenador",
        papel_coordenador=ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL,
        status="ativo",
        status_suspensao=False,
    )

    client.force_login(user)
    response = client.get(reverse("dashboard:admin_dashboard"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates if template.name]
    assert "dashboard/coordenadores_dashboard.html" in template_names

    page = response.content.decode()
    assert "Dashboard do coordenador" in page

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import UserType
from organizacoes.models import Organizacao
from nucleos.models import Nucleo, ParticipacaoNucleo

pytestmark = pytest.mark.django_db


def create_user(email: str, username: str, user_type: UserType, **extra):
    User = get_user_model()
    return User.objects.create_user(
        email=email,
        username=username,
        password="pwd",
        user_type=user_type,
        **extra,
    )


def test_admin_list_membros(client):
    admin = create_user("admin@example.com", "admin", UserType.ADMIN)
    assoc = create_user(
        "assoc@example.com",
        "assoc",
        UserType.ASSOCIADO,
        is_associado=True,
    )
    client.force_login(admin)
    resp = client.get(reverse("membros:membros_lista"))
    assert resp.status_code == 200
    assert assoc.username in resp.content.decode()


def test_search_membros(client):
    admin = create_user("a2@example.com", "a2", UserType.ADMIN)
    create_user("john@example.com", "john", UserType.ASSOCIADO, is_associado=True)
    create_user("jane@example.com", "jane", UserType.ASSOCIADO, is_associado=True)
    client.force_login(admin)
    resp = client.get(reverse("membros:membros_lista"), {"q": "john"})
    content = resp.content.decode()
    assert "john" in content
    assert "jane" not in content


def test_coordenador_list_membros(client):
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
    coord = create_user(
        "coord@example.com",
        "coord",
        UserType.COORDENADOR,
        organizacao=org,
    )
    assoc = create_user(
        "assoc2@example.com",
        "assoc2",
        UserType.ASSOCIADO,
        is_associado=True,
        organizacao=org,
    )
    client.force_login(coord)
    resp = client.get(reverse("membros:membros_lista"))
    assert resp.status_code == 200
    assert assoc.username in resp.content.decode()


def test_associados_sections_grouping(client):
    org = Organizacao.objects.create(nome="Org Filters", cnpj="11.111.111/1111-11")
    nucleo = Nucleo.objects.create(organizacao=org, nome="Núcleo Alpha")
    admin = create_user(
        "filters-admin@example.com",
        "filters-admin",
        UserType.ADMIN,
        organizacao=org,
    )
    associado = create_user(
        "assoc-sem-nucleo@example.com",
        "assoc-sem-nucleo",
        UserType.ASSOCIADO,
        is_associado=True,
        organizacao=org,
    )
    nucleado = create_user(
        "assoc-com-nucleo@example.com",
        "assoc-com-nucleo",
        UserType.ASSOCIADO,
        is_associado=True,
        organizacao=org,
        nucleo=nucleo,
    )
    ParticipacaoNucleo.objects.create(
        user=nucleado,
        nucleo=nucleo,
        status="ativo",
        status_suspensao=False,
    )
    nucleado_sem_campo = create_user(
        "assoc-participacao@example.com",
        "assoc-participacao",
        UserType.ASSOCIADO,
        is_associado=True,
        organizacao=org,
    )
    ParticipacaoNucleo.objects.create(
        user=nucleado_sem_campo,
        nucleo=nucleo,
        status="ativo",
        status_suspensao=False,
    )
    consultor = create_user(
        "consultor@example.com",
        "consultor",
        UserType.CONSULTOR,
        organizacao=org,
    )
    coordenador = create_user(
        "coordenador@example.com",
        "coordenador",
        UserType.COORDENADOR,
        organizacao=org,
        is_coordenador=True,
    )

    client.force_login(admin)
    resp = client.get(reverse("membros:membros_lista"))

    assert resp.status_code == 200
    content = resp.content.decode()

    def section_content(html: str, section: str) -> str:
        marker = f'data-associados-section="{section}"'
        assert marker in html
        after_marker = html.split(marker, 1)[1]
        closing_index = after_marker.find("</details>")
        assert closing_index != -1
        return after_marker[:closing_index]

    sem_nucleo_section = section_content(content, "sem-nucleo")
    assert associado.username in sem_nucleo_section
    assert nucleado.username not in sem_nucleo_section
    assert nucleado_sem_campo.username not in sem_nucleo_section
    assert consultor.username not in sem_nucleo_section
    assert coordenador.username not in sem_nucleo_section

    nucleados_section = section_content(content, "nucleados")
    assert nucleado.username in nucleados_section
    assert nucleado_sem_campo.username in nucleados_section
    assert associado.username not in nucleados_section
    assert consultor.username not in nucleados_section
    assert coordenador.username not in nucleados_section

    consultores_section = section_content(content, "consultores")
    assert consultor.username in consultores_section
    assert associado.username not in consultores_section
    assert nucleado.username not in consultores_section
    assert coordenador.username not in consultores_section

    coordenadores_section = section_content(content, "coordenadores")
    assert coordenador.username in coordenadores_section
    assert associado.username not in coordenadores_section
    assert nucleado.username not in coordenadores_section
    assert consultor.username not in coordenadores_section

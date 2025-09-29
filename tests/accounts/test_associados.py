import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import UserType
from organizacoes.models import Organizacao
from nucleos.models import Nucleo

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


def test_admin_list_associados(client):
    admin = create_user("admin@example.com", "admin", UserType.ADMIN)
    assoc = create_user(
        "assoc@example.com",
        "assoc",
        UserType.ASSOCIADO,
        is_associado=True,
    )
    client.force_login(admin)
    resp = client.get(reverse("accounts:associados_lista"))
    assert resp.status_code == 200
    assert assoc.username in resp.content.decode()


def test_search_associados(client):
    admin = create_user("a2@example.com", "a2", UserType.ADMIN)
    create_user("john@example.com", "john", UserType.ASSOCIADO, is_associado=True)
    create_user("jane@example.com", "jane", UserType.ASSOCIADO, is_associado=True)
    client.force_login(admin)
    resp = client.get(reverse("accounts:associados_lista"), {"q": "john"})
    content = resp.content.decode()
    assert "john" in content
    assert "jane" not in content


def test_coordenador_list_associados(client):
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")
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
    resp = client.get(reverse("accounts:associados_lista"))
    assert resp.status_code == 200
    assert assoc.username in resp.content.decode()


def test_associados_htmx_returns_partial_grid(client):
    admin = create_user("htmx-admin@example.com", "htmx-admin", UserType.ADMIN)
    for idx in range(11):
        create_user(
            f"assoc-htmx-{idx}@example.com",
            f"assoc-htmx-{idx}",
            UserType.ASSOCIADO,
            is_associado=True,
        )

    client.force_login(admin)
    url = reverse("accounts:associados_lista")
    resp = client.get(url, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    template_names = [template.name for template in resp.templates if getattr(template, "name", None)]
    assert "associados/_grid.html" in template_names
    assert "associados/associado_list.html" not in template_names

    content = resp.content.decode()
    assert "card-grid" in content
    assert "assoc-htmx-0" in content
    assert 'hx-target="#associados-grid"' in content
    assert f'hx-get="{url}?page=2' in content
    assert 'hx-indicator="#associados-loading"' in content
    assert 'hx-swap-oob="true"' in content


def test_associados_filter_actions(client):
    org = Organizacao.objects.create(nome="Org Filters", cnpj="11.111.111/1111-11", slug="org-filters")
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
    url = reverse("accounts:associados_lista")

    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert 'data-associados-filter-card="associados"' in content
    assert 'data-associados-filter-card="nucleados"' in content
    assert 'data-associados-filter-card="consultores"' in content
    assert 'data-associados-filter-card="coordenadores"' in content
    assert resp.context["associados_filter_url"].endswith("?tipo=associados")
    assert resp.context["nucleados_filter_url"].endswith("?tipo=nucleados")
    assert resp.context["consultores_filter_url"].endswith("?tipo=consultores")
    assert resp.context["coordenadores_filter_url"].endswith("?tipo=coordenadores")
    assert 'id="associados-filter-state"' in content

    resp = client.get(url, {"tipo": "associados"})
    content = resp.content.decode()
    assert associado.username in content
    assert nucleado.username not in content
    assert "consultor@example.com" not in content
    assert "coordenador@example.com" not in content

    resp = client.get(url, {"tipo": "nucleados"})
    content = resp.content.decode()
    assert nucleado.username in content
    assert associado.username not in content
    assert "consultor@example.com" not in content

    resp = client.get(url, {"tipo": "consultores"})
    content = resp.content.decode()
    assert "consultor@example.com" in content
    assert associado.username not in content
    assert nucleado.username not in content

    resp = client.get(url, {"tipo": "coordenadores"})
    content = resp.content.decode()
    assert "coordenador@example.com" in content
    assert "consultor@example.com" not in content
    assert associado.username not in content
    assert nucleado.username not in content

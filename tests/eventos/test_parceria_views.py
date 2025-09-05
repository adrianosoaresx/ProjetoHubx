from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import UserType
from eventos.factories import EventoFactory
from eventos.models import ParceriaEvento
from empresas.factories import EmpresaFactory
from organizacoes.factories import OrganizacaoFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return OrganizacaoFactory()


@pytest.fixture
def admin_user(organizacao):
    return User.objects.create_user(
        username="admin",
        email="admin@ex.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


def test_parceria_list_filtra_organizacao(client, admin_user, organizacao):
    outra_org = OrganizacaoFactory()
    outro_user = User.objects.create_user(
        username="x",
        email="x@ex.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=outra_org,
    )
    evento1 = EventoFactory(organizacao=organizacao, coordenador=admin_user)
    evento2 = EventoFactory(organizacao=outra_org, coordenador=outro_user)
    empresa1 = EmpresaFactory(organizacao=organizacao)
    empresa2 = EmpresaFactory(organizacao=outra_org)
    ParceriaEvento.objects.create(
        evento=evento1,
        empresa=empresa1,
        cnpj="12345678000199",
        contato="c",
        representante_legal="r",
        data_inicio=date.today(),
        data_fim=date.today() + timedelta(days=1),
    )
    ParceriaEvento.objects.create(
        evento=evento2,
        empresa=empresa2,
        cnpj="22345678000199",
        contato="c",
        representante_legal="r",
        data_inicio=date.today(),
        data_fim=date.today() + timedelta(days=1),
    )
    client.force_login(admin_user)
    resp = client.get(reverse("eventos:parceria_list"))
    html = resp.content.decode()
    assert empresa1.nome in html
    assert empresa2.nome not in html


def test_parceria_create_requires_admin(client, organizacao):
    user = User.objects.create_user(
        username="u",
        email="u@ex.com",
        password="pass",
        organizacao=organizacao,
        user_type=UserType.ASSOCIADO,
    )
    client.force_login(user)
    resp = client.get(reverse("eventos:parceria_criar"))
    assert resp.status_code == 403


def test_parceria_create(client, admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    empresa = EmpresaFactory(organizacao=admin_user.organizacao)
    url = reverse("eventos:parceria_criar")
    data = {
        "evento": evento.id,
        "empresa": empresa.id,
        "cnpj": "12345678000199",
        "contato": "Contato",
        "representante_legal": "Rep",
        "data_inicio": date.today(),
        "data_fim": date.today() + timedelta(days=1),
        "tipo_parceria": "patrocinio",
        "descricao": "",
    }
    client.force_login(admin_user)
    resp = client.post(url, data)
    assert resp.status_code == 302
    assert ParceriaEvento.objects.filter(evento=evento, empresa=empresa).exists()

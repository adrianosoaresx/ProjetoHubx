import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from datetime import date, timedelta

from accounts.models import UserType
from agenda.factories import EventoFactory
from agenda.forms import ParceriaEventoForm
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
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def api_client():
    return APIClient()


def _form_data(evento, empresa):
    return {
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


def test_parceria_form_rejeita_mime_divergente(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    empresa = EmpresaFactory(organizacao=admin_user.organizacao)
    arquivo = SimpleUploadedFile("fake.png", b"%PDF-1.4", content_type="application/pdf")
    form = ParceriaEventoForm(data=_form_data(evento, empresa), files={"acordo": arquivo})
    assert not form.is_valid()
    assert "Extensão" in form.errors["acordo"][0]


def test_parceria_api_rejeita_mime_divergente(api_client, admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    empresa = EmpresaFactory(organizacao=admin_user.organizacao)
    arquivo = SimpleUploadedFile("fake.png", b"%PDF-1.4", content_type="application/pdf")
    data = _form_data(evento, empresa)
    data["acordo"] = arquivo
    api_client.force_authenticate(admin_user)
    url = reverse("agenda_api:parceria-list")
    resp = api_client.post(url, data, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Extensão" in resp.data["acordo"][0]

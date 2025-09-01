import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserType
from agenda.factories import EventoFactory
from agenda.forms import InscricaoEventoForm
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
def cliente_user(organizacao):
    return User.objects.create_user(
        username="cliente",
        email="cliente@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )


@pytest.fixture
def api_client():
    return APIClient()


def _form_data():
    return {"valor_pago": "10.00", "metodo_pagamento": "pix", "observacao": ""}


def test_inscricao_form_rejeita_mime_divergente(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    arquivo = SimpleUploadedFile("fake.png", b"%PDF-1.4", content_type="application/pdf")
    form = InscricaoEventoForm(data=_form_data(), files={"comprovante_pagamento": arquivo})
    assert not form.is_valid()
    assert "Extensão" in form.errors["comprovante_pagamento"][0]


def test_inscricao_api_rejeita_mime_divergente(api_client, cliente_user):
    evento = EventoFactory(organizacao=cliente_user.organizacao, coordenador=cliente_user)
    arquivo = SimpleUploadedFile("fake.png", b"%PDF-1.4", content_type="application/pdf")
    data = {"evento": evento.id, "comprovante_pagamento": arquivo}
    api_client.force_authenticate(cliente_user)
    url = reverse("agenda_api:inscricao-list")
    resp = api_client.post(url, data, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Extensão" in resp.data["comprovante_pagamento"][0]

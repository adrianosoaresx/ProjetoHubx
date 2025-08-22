import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserType
from agenda.factories import EventoFactory
from agenda.forms import MaterialDivulgacaoEventoForm
from agenda.models import MaterialDivulgacaoEvento
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


def _form_data(evento):
    return {
        "evento": evento.id,
        "titulo": "Mat",
        "descricao": "",
        "tipo": "banner",
        "tags": "",
    }


def test_material_form_rejeita_extensao_invalida(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    arquivo = SimpleUploadedFile("malware.exe", b"xx", content_type="application/octet-stream")
    form = MaterialDivulgacaoEventoForm(data=_form_data(evento), files={"arquivo": arquivo})
    assert not form.is_valid()
    assert "Tipo" in form.errors["arquivo"][0]


def test_material_form_rejeita_mime_divergente(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    arquivo = SimpleUploadedFile("img.png", b"%PDF-1.4", content_type="application/pdf")
    form = MaterialDivulgacaoEventoForm(data=_form_data(evento), files={"arquivo": arquivo})
    assert not form.is_valid()
    assert "Extensão" in form.errors["arquivo"][0]


def test_material_form_limita_tamanho_imagem(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    big_content = b"a" * (10 * 1024 * 1024 + 1)
    arquivo = SimpleUploadedFile("big.png", big_content, content_type="image/png")
    form = MaterialDivulgacaoEventoForm(data=_form_data(evento), files={"arquivo": arquivo})
    assert not form.is_valid()
    assert "tamanho" in form.errors["arquivo"][0]


def test_list_view_exibe_apenas_aprovados(client, cliente_user, admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    file_ok = SimpleUploadedFile("ok.pdf", b"%PDF-1.4", content_type="application/pdf")
    MaterialDivulgacaoEvento.objects.create(
        evento=evento,
        titulo="Mat OK",
        tipo="banner",
        arquivo=file_ok,
        status="aprovado",
    )
    file_pend = SimpleUploadedFile("pend.pdf", b"%PDF-1.4", content_type="application/pdf")
    MaterialDivulgacaoEvento.objects.create(
        evento=evento,
        titulo="Mat Criado",
        tipo="banner",
        arquivo=file_pend,
        status="criado",
    )
    client.force_login(cliente_user)
    resp = client.get(reverse("agenda:material_list"))
    html = resp.content.decode()
    assert "Mat OK" in html
    assert "Aprovado" in html
    assert "Mat Criado" not in html
    assert "Criado" not in html


def test_list_view_filtra_por_organizacao(client, admin_user, organizacao):
    outra_org = OrganizacaoFactory()
    outro_user = User.objects.create_user(
        username="x",
        email="x@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=outra_org,
    )
    evento1 = EventoFactory(organizacao=organizacao, coordenador=admin_user)
    evento2 = EventoFactory(organizacao=outra_org, coordenador=outro_user)
    file_ok = SimpleUploadedFile("ok.pdf", b"%PDF-1.4", content_type="application/pdf")
    MaterialDivulgacaoEvento.objects.create(
        evento=evento1,
        titulo="Org1",
        tipo="banner",
        arquivo=file_ok,
        status="aprovado",
    )
    MaterialDivulgacaoEvento.objects.create(
        evento=evento2,
        titulo="Org2",
        tipo="banner",
        arquivo=file_ok,
        status="aprovado",
    )
    client.force_login(admin_user)
    resp = client.get(reverse("agenda:material_list"))
    html = resp.content.decode()
    assert "Org1" in html
    assert "Org2" not in html


def test_material_api_rejeita_extensao_invalida(api_client, admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    arquivo = SimpleUploadedFile("malware.exe", b"xx", content_type="application/octet-stream")
    data = _form_data(evento)
    data["arquivo"] = arquivo
    api_client.force_authenticate(admin_user)
    url = reverse("agenda_api:material-list")
    resp = api_client.post(url, data, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Tipo" in resp.data["arquivo"][0]


def test_material_api_rejeita_mime_divergente(api_client, admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    arquivo = SimpleUploadedFile("img.png", b"%PDF-1.4", content_type="application/pdf")
    data = _form_data(evento)
    data["arquivo"] = arquivo
    api_client.force_authenticate(admin_user)
    url = reverse("agenda_api:material-list")
    resp = api_client.post(url, data, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Extensão" in resp.data["arquivo"][0]


def test_material_api_limita_tamanho_imagem(api_client, admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    big_content = b"a" * (10 * 1024 * 1024 + 1)
    arquivo = SimpleUploadedFile("big.png", big_content, content_type="image/png")
    data = _form_data(evento)
    data["arquivo"] = arquivo
    api_client.force_authenticate(admin_user)
    url = reverse("agenda_api:material-list")
    resp = api_client.post(url, data, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "tamanho" in resp.data["arquivo"][0]


def test_material_api_limita_tamanho_pdf(api_client, admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    big_content = b"a" * (20 * 1024 * 1024 + 1)
    arquivo = SimpleUploadedFile("big.pdf", big_content, content_type="application/pdf")
    data = _form_data(evento)
    data["arquivo"] = arquivo
    api_client.force_authenticate(admin_user)
    url = reverse("agenda_api:material-list")
    resp = api_client.post(url, data, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "tamanho" in resp.data["arquivo"][0]

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import UserType
from agenda.forms import MaterialDivulgacaoEventoForm
from agenda.models import MaterialDivulgacaoEvento
from agenda.factories import EventoFactory
from organizacoes.factories import OrganizacaoFactory
from django.contrib.auth import get_user_model

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
def cliente_user():
    return User.objects.create_user(
        username="cliente",
        email="cliente@example.com",
        password="pass",
        user_type=UserType.CONVIDADO,
    )


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
    assert "Formato" in form.errors["arquivo"][0]


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
        titulo="Aprovado",
        tipo="banner",
        arquivo=file_ok,
        status="aprovado",
    )
    file_pend = SimpleUploadedFile("pend.pdf", b"%PDF-1.4", content_type="application/pdf")
    MaterialDivulgacaoEvento.objects.create(
        evento=evento,
        titulo="Criado",
        tipo="banner",
        arquivo=file_pend,
        status="criado",
    )
    client.force_login(cliente_user)
    resp = client.get(reverse("agenda:material_list"))
    assert "Aprovado" in resp.content.decode()
    assert "Criado" not in resp.content.decode()

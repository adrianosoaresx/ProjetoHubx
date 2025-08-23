import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from validate_docbr import CNPJ

from accounts.models import UserType
from agenda.factories import EventoFactory
from agenda.forms import ParceriaEventoForm
from empresas.factories import EmpresaFactory
from organizacoes.factories import OrganizacaoFactory

User = get_user_model()


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


def _form_data(evento, empresa, cnpj):
    return {
        "evento": evento.id,
        "empresa": empresa.id,
        "cnpj": cnpj,
        "contato": "Contato",
        "representante_legal": "Rep",
        "data_inicio": date.today(),
        "data_fim": date.today() + timedelta(days=1),
        "tipo_parceria": "patrocinio",
        "descricao": "",
    }


@pytest.mark.django_db
def test_parceria_form_cnpj_valido(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    empresa = EmpresaFactory(organizacao=admin_user.organizacao)
    cnpj_num = CNPJ().generate()
    form = ParceriaEventoForm(data=_form_data(evento, empresa, cnpj_num))
    assert form.is_valid()
    assert form.cleaned_data["cnpj"] == cnpj_num


@pytest.mark.django_db
def test_parceria_form_cnpj_invalido(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    empresa = EmpresaFactory(organizacao=admin_user.organizacao)
    form = ParceriaEventoForm(data=_form_data(evento, empresa, "12345678000100"))
    assert not form.is_valid()
    assert "cnpj" in form.errors


@pytest.mark.django_db
def test_parceria_form_cnpj_apenas_digitos(admin_user):
    evento = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
    empresa = EmpresaFactory(organizacao=admin_user.organizacao)
    form = ParceriaEventoForm(data=_form_data(evento, empresa, "12.345.678/0001-99"))
    assert not form.is_valid()
    assert "cnpj" in form.errors

import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from agenda.models import Evento
from discussao.models import CategoriaDiscussao
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

User = get_user_model()


@pytest.fixture
def organizacao(db):
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-99", slug="org")


@pytest.fixture
def outra_organizacao(db):
    return Organizacao.objects.create(nome="Outra", cnpj="00.000.000/0002-99", slug="outra")


@pytest.fixture
def nucleo(organizacao):
    return Nucleo.objects.create(nome="Nucleo", organizacao=organizacao)


@pytest.fixture
def evento(organizacao, nucleo):
    return Evento.objects.create(
        organizacao=organizacao,
        nucleo=nucleo,
        coordenador=None,
        titulo="Evento",
        descricao="",
        data_inicio="2024-01-01",
        data_fim="2024-01-02",
        endereco="",
        cidade="",
        estado="SC",
        cep="00000-000",
        status=0,
        publico_alvo=0,
        numero_convidados=0,
        numero_presentes=0,
        valor_ingresso=0,
        orcamento=0,
    )


@pytest.fixture
def root_user(organizacao):
    return User.objects.create_superuser(
        email="root@example.com",
        username="root",
        password="pass",
        organizacao=organizacao,
    )


@pytest.fixture
def admin_user(organizacao):
    return User.objects.create_user(
        email="admin@example.com",
        username="admin",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def coordenador_user(organizacao, nucleo):
    return User.objects.create_user(
        email="coord@example.com",
        username="coord",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
        nucleo=nucleo,
    )


@pytest.fixture
def associado_user(organizacao):
    return User.objects.create_user(
        email="assoc@example.com",
        username="assoc",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )


@pytest.fixture
def nucleado_user(organizacao, nucleo):
    return User.objects.create_user(
        email="nuc@example.com",
        username="nuc",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
        nucleo=nucleo,
    )


@pytest.fixture(autouse=True)
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def categoria(organizacao):
    return CategoriaDiscussao.objects.create(nome="Cat", organizacao=organizacao)


@pytest.fixture(autouse=True)
def patch_templates(monkeypatch):
    from discussao import views

    monkeypatch.setattr(views.CategoriaListView, "template_name", "base.html", raising=False)
    monkeypatch.setattr(views.TopicoListView, "template_name", "base.html", raising=False)
    monkeypatch.setattr(views.TopicoDetailView, "template_name", "base.html", raising=False)
    monkeypatch.setattr(views.TopicoCreateView, "template_name", "base.html", raising=False)
    monkeypatch.setattr(views.TopicoUpdateView, "template_name", "base.html", raising=False)
    monkeypatch.setattr(views.TopicoDeleteView, "template_name", "base.html", raising=False)
    monkeypatch.setattr(views.RespostaCreateView, "template_name", "base.html", raising=False)

    monkeypatch.setattr(
        views.TopicoUpdateView,
        "get_object",
        lambda self, queryset=None: self.object,
        raising=False,
    )
    monkeypatch.setattr(
        views.TopicoDeleteView,
        "get_object",
        lambda self, queryset=None: self.object,
        raising=False,
    )

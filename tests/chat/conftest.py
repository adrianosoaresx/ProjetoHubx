import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from accounts.models import UserType
from agenda.models import Evento
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture(autouse=True)
def in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@pytest.fixture(autouse=True)
def default_participacoes(admin_user, coordenador_user, nucleo):
    ParticipacaoNucleo.objects.get_or_create(
        user=admin_user, nucleo=nucleo, defaults={"status": "ativo"}
    )
    ParticipacaoNucleo.objects.get_or_create(
        user=coordenador_user, nucleo=nucleo, defaults={"status": "ativo"}
    )


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")


@pytest.fixture
def nucleo(organizacao):
    return Nucleo.objects.create(nome="Nuc", slug="nuc", organizacao=organizacao)


@pytest.fixture
def evento(organizacao, nucleo, admin_user):
    return Evento.objects.create(
        titulo="Evento",
        descricao="",
        data_inicio=now(),
        data_fim=now(),
        local="Rua 1",
        cidade="Cidade",
        estado="SC",
        cep="00000-000",
        coordenador=admin_user,
        organizacao=organizacao,
        nucleo=nucleo,
        status=0,
        publico_alvo=0,
        numero_convidados=0,
        numero_presentes=0,
        valor_ingresso=0,
        orcamento=0,
        contato_nome="Coord",
    )


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
def coordenador_user(organizacao, nucleo):
    return User.objects.create_user(
        username="coord",
        email="coord@example.com",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
        nucleo=nucleo,
    )


@pytest.fixture
def associado_user(organizacao):
    return User.objects.create_user(
        username="assoc",
        email="assoc@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )

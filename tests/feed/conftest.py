import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from agenda.factories import EventoFactory
from feed.models import Post
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao

User = get_user_model()


@pytest.fixture(autouse=True)
def add_nucleos_property():
    if not hasattr(User, "nucleos"):
        User.add_to_class("nucleos", property(lambda self: Nucleo.objects.filter(participacoes__user=self)))
    if not hasattr(User, "eventos"):
        from agenda.models import Evento

        User.add_to_class("eventos", property(lambda self: Evento.objects.filter(organizacao=self.organizacao)))


@pytest.fixture
def organizacao(db):
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-01", slug="org")


@pytest.fixture
def root_user(db, organizacao):
    return User.objects.create_superuser(
        email="root@example.com",
        username="root",
        password="pass",
        organizacao=organizacao,
    )


@pytest.fixture
def admin_user(db, organizacao):
    return User.objects.create_user(
        email="admin@example.com",
        username="admin",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def coordenador_user(db, organizacao):
    return User.objects.create_user(
        email="coord@example.com",
        username="coord",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )


@pytest.fixture
def associado_user(db, organizacao):
    return User.objects.create_user(
        email="assoc@example.com",
        username="assoc",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )


@pytest.fixture
def nucleado_user(db, organizacao):
    return User.objects.create_user(
        email="nucleo@example.com",
        username="nucleo",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


@pytest.fixture
def nucleo(db, organizacao, coordenador_user, nucleado_user):
    n = Nucleo.objects.create(nome="N1", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=nucleado_user, nucleo=n, papel="membro", status="ativo")
    ParticipacaoNucleo.objects.create(user=coordenador_user, nucleo=n, papel="coordenador", status="ativo")
    return n


@pytest.fixture
def evento(db, organizacao, nucleo, admin_user):
    return EventoFactory(organizacao=organizacao, nucleo=nucleo, coordenador=admin_user)


@pytest.fixture(autouse=True)
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def posts(admin_user, nucleado_user, nucleo, evento, organizacao):
    p1 = Post.objects.create(autor=admin_user, organizacao=organizacao, tipo_feed="global", conteudo="g")
    p2 = Post.objects.create(autor=nucleado_user, organizacao=organizacao, tipo_feed="usuario", conteudo="u")
    p3 = Post.objects.create(
        autor=nucleado_user, organizacao=organizacao, tipo_feed="nucleo", nucleo=nucleo, conteudo="n"
    )
    p4 = Post.objects.create(
        autor=nucleado_user, organizacao=organizacao, tipo_feed="evento", evento=evento, conteudo="e"
    )
    for p in (p1, p2, p3, p4):
        p.moderacao.status = "aprovado"
        p.moderacao.save()
    return p1, p2, p3, p4

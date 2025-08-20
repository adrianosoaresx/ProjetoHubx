import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User, UserType
from agenda.models import Evento
from empresas.models import Empresa
from feed.models import Post
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def faker_ptbr():
    from faker import Faker

    return Faker("pt_BR")


@pytest.fixture(autouse=True)
def no_celery(monkeypatch):
    monkeypatch.setattr("organizacoes.tasks.enviar_email_membros.delay", lambda *a, **k: None)


@pytest.fixture
def superadmin_user():
    client = Client()
    user = User.objects.create_user(
        username="root",
        email="root@example.com",
        password="pass",
        user_type=UserType.ROOT,
    )
    client.force_login(user)
    return client


@pytest.fixture
def admin_user(organizacao):
    client = Client()
    user = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    client.force_login(user)
    return client


@pytest.fixture
def organizacao(faker_ptbr):
    name = faker_ptbr.company()
    return Organizacao.objects.create(nome=name, cnpj=faker_ptbr.cnpj(), slug=slugify(name))


def test_list_view_superadmin(superadmin_user, organizacao, faker_ptbr):
    org_inativa = Organizacao.objects.create(
        nome="Inativa",
        cnpj=faker_ptbr.cnpj(),
        slug="inativa",
        inativa=True,
        inativada_em=timezone.now(),
    )
    Organizacao.objects.create(
        nome="Excluida",
        cnpj=faker_ptbr.cnpj(),
        slug="excluida",
        deleted=True,
    )
    url = reverse("organizacoes:list")
    response = superadmin_user.get(url)
    assert response.status_code == 200
    objs = response.context["object_list"]
    assert organizacao in objs
    assert not any(o.slug == "inativa" for o in objs)
    assert not any(o.slug == "excluida" for o in objs)


def test_list_view_admin_access(admin_user):
    url = reverse("organizacoes:list")
    response = admin_user.get(url)
    assert response.status_code == 200


def test_create_view_superadmin(superadmin_user, faker_ptbr):
    url = reverse("organizacoes:create")
    data = {"nome": "Nova Org", "cnpj": faker_ptbr.cnpj(), "slug": "nova-org"}
    response = superadmin_user.post(url, data=data, follow=True)
    assert response.status_code == 200
    assert Organizacao.objects.filter(nome="Nova Org").exists()
    msgs = list(response.context["messages"])
    assert any("criada" in m.message.lower() for m in msgs)


def test_create_view_denied_for_admin(admin_user, faker_ptbr):
    url = reverse("organizacoes:create")
    data = {"nome": "Org X", "cnpj": faker_ptbr.cnpj(), "slug": "org-x"}
    response = admin_user.post(url, data=data)
    assert response.status_code == 403
    assert not Organizacao.objects.filter(nome="Org X").exists()


def test_update_view_superadmin(superadmin_user, organizacao):
    url = reverse("organizacoes:update", args=[organizacao.pk])
    response = superadmin_user.post(
        url,
        {"nome": "Editada", "cnpj": organizacao.cnpj, "slug": "editada"},
        follow=True,
    )
    assert response.status_code == 200
    organizacao.refresh_from_db()
    assert organizacao.nome == "Editada"
    msgs = list(response.context["messages"])
    assert any("atualizada" in m.message.lower() for m in msgs)


def test_update_view_denied_for_admin(admin_user, organizacao):
    url = reverse("organizacoes:update", args=[organizacao.pk])
    response = admin_user.post(url, {"nome": "X", "cnpj": organizacao.cnpj, "slug": "x"})
    assert response.status_code == 403
    organizacao.refresh_from_db()
    assert organizacao.nome != "X"


def test_delete_view_superadmin(superadmin_user, organizacao):
    url = reverse("organizacoes:delete", args=[organizacao.pk])
    response = superadmin_user.post(url, follow=True)
    assert response.status_code == 200
    organizacao.refresh_from_db()
    assert organizacao.deleted is True and organizacao.deleted_at is not None


def test_delete_view_denied_for_admin(admin_user, organizacao):
    url = reverse("organizacoes:delete", args=[organizacao.pk])
    response = admin_user.post(url)
    assert response.status_code == 403
    assert Organizacao.objects.filter(pk=organizacao.pk).exists()


def test_create_template_fields(superadmin_user):
    url = reverse("organizacoes:create")
    resp = superadmin_user.get(url)
    html = resp.content.decode()
    for field in [
        "nome",
        "cnpj",
        "descricao",
        "slug",
        "tipo",
        "rua",
        "cidade",
        "estado",
        "contato_nome",
        "contato_email",
        "contato_telefone",
        "avatar",
        "cover",
    ]:
        assert f'name="{field}"' in html
    assert 'name="logo"' not in html


def test_list_template_avatar_and_tipo(superadmin_user, faker_ptbr, tmp_path):
    avatar = SimpleUploadedFile("a.png", b"x", content_type="image/png")
    org1 = Organizacao.objects.create(
        nome="Alpha",
        cnpj=faker_ptbr.cnpj(),
        slug="alpha",
        avatar=avatar,
        tipo="ong",
    )
    org2 = Organizacao.objects.create(
        nome="Beta",
        cnpj=faker_ptbr.cnpj(),
        slug="beta",
        tipo="empresa",
    )
    resp = superadmin_user.get(reverse("organizacoes:list"))
    content = resp.content.decode()
    assert org1.get_tipo_display() in content
    assert org2.get_tipo_display() in content
    assert "img" in content  # avatar shown
    assert ">B<" in content  # initial for org2


def test_ordering_by_nome(superadmin_user, faker_ptbr):
    Organizacao.objects.create(nome="A Org", cnpj=faker_ptbr.cnpj(), slug="a-org")
    Organizacao.objects.create(nome="B Org", cnpj=faker_ptbr.cnpj(), slug="b-org")
    resp = superadmin_user.get(reverse("organizacoes:list"))
    objs = list(resp.context["object_list"])
    assert objs[0].nome == "A Org"


def test_list_search(superadmin_user, faker_ptbr):
    org_a = Organizacao.objects.create(nome="Alpha Org", cnpj=faker_ptbr.cnpj(), slug="alpha-slug")
    org_b = Organizacao.objects.create(nome="Beta Org", cnpj=faker_ptbr.cnpj(), slug="beta-slug")
    # search by slug
    resp = superadmin_user.get(reverse("organizacoes:list") + "?q=alpha-slug")
    content = resp.content.decode()
    assert org_a.nome in content and org_b.nome not in content
    # search by name
    resp2 = superadmin_user.get(reverse("organizacoes:list") + "?q=Beta")
    content2 = resp2.content.decode()
    assert org_b.nome in content2 and org_a.nome not in content2


def test_list_pagination(superadmin_user, faker_ptbr):
    for i in range(12):
        Organizacao.objects.create(nome=f"Org {i}", cnpj=faker_ptbr.cnpj(), slug=f"org-{i}")
    url = reverse("organizacoes:list")
    resp1 = superadmin_user.get(url)
    assert len(resp1.context["object_list"]) == 10
    resp2 = superadmin_user.get(url + "?page=2")
    assert len(resp2.context["object_list"]) == 2


def test_detail_view_admin_access(admin_user, organizacao):
    url = reverse("organizacoes:detail", args=[organizacao.pk])
    resp = admin_user.get(url)
    assert resp.status_code == 200
    assert organizacao.nome in resp.content.decode()


def test_toggle_active_and_logs(superadmin_user, organizacao):
    url = reverse("organizacoes:toggle", args=[organizacao.pk])
    resp = superadmin_user.post(url, follow=True)
    assert resp.status_code == 200
    organizacao.refresh_from_db()
    assert organizacao.inativa is True
    log = organizacao.atividade_logs.first()
    assert log.acao == "inactivated"


def test_toggle_denied_for_admin(admin_user, organizacao):
    url = reverse("organizacoes:toggle", args=[organizacao.pk])
    resp = admin_user.post(url)
    assert resp.status_code == 403


def test_logs_view_permission(superadmin_user, admin_user, organizacao):
    url = reverse("organizacoes:historico", args=[organizacao.pk])
    assert superadmin_user.get(url).status_code == 200
    assert admin_user.get(url).status_code == 403


def test_signal_emitted_on_create(monkeypatch, superadmin_user, faker_ptbr):
    called = {}

    def fake_delay(org_id, acao):
        called["called"] = True

    monkeypatch.setattr("organizacoes.tasks.enviar_email_membros.delay", fake_delay)
    url = reverse("organizacoes:create")
    data = {"nome": "Org", "cnpj": faker_ptbr.cnpj(), "slug": "org"}
    superadmin_user.post(url, data=data, follow=True)
    assert called.get("called") is True


def test_detail_view_lists_associations(superadmin_user, faker_ptbr):
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="org")
    user = User.objects.create_user(
        username="u1",
        email="u1@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=org,
    )
    Nucleo.objects.create(organizacao=org, nome="N1", slug="n1")
    Empresa.objects.create(
        organizacao=org,
        usuario=user,
        nome="E1",
        cnpj=faker_ptbr.cnpj(),
        tipo="",
        municipio="Cidade",
        estado="SC",
    )
    Post.objects.create(organizacao=org, autor=user, conteudo="p", tipo_feed="global")
    Evento.objects.create(
        organizacao=org,
        coordenador=user,
        titulo="Ev",
        descricao="d",
        data_inicio=timezone.now(),
        data_fim=timezone.now(),
        local="loc",
        cidade="Cidade",
        estado="SC",
        cep="12345-000",
        status=0,
        publico_alvo=0,
        numero_convidados=0,
        numero_presentes=0,
        contato_nome="c",
    )
    resp = superadmin_user.get(reverse("organizacoes:detail", args=[org.pk]))
    content = resp.content.decode()
    assert "Membros" in content and "Núcleos" in content and "Eventos" in content

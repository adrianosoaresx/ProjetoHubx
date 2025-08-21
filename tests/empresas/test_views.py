import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from validate_docbr import CNPJ

from empresas.factories import EmpresaFactory
from empresas.models import AvaliacaoEmpresa, Empresa, EmpresaChangeLog


@pytest.mark.django_db
def test_buscar_view_returns_results(client, admin_user):
    EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Alpha")
    client.force_login(admin_user)
    resp = client.get(reverse("empresas:buscar"), {"q": "Alpha"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert "Alpha" in resp.content.decode()


@pytest.mark.django_db
def test_list_filters_name_municipio_tags(client, admin_user, tag_factory):
    tag1 = tag_factory(nome="Tech")
    tag2 = tag_factory(nome="Food")
    e1 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Alpha", municipio="X")
    e1.tags.add(tag1)
    e2 = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Beta", municipio="Y")
    e2.tags.add(tag2)
    client.force_login(admin_user)
    resp = client.get(reverse("empresas:lista"), {"nome": "Alpha", "municipio": "X", "tags": [tag1.id]})
    content = resp.content.decode()
    assert "Alpha" in content
    assert "Beta" not in content


@pytest.mark.django_db
def test_create_empresa_sets_user_and_org(client, nucleado_user):
    client.force_login(nucleado_user)
    cnpj = CNPJ().generate()
    data = {
        "nome": "Nova",
        "cnpj": cnpj,
        "tipo": "mei",
        "municipio": "Cidade",
        "estado": "SP",
        "descricao": "",
        "palavras_chave": "",
        "tags": [],
    }
    resp = client.post(reverse("empresas:empresa_criar"), data)
    assert resp.status_code in (302, 200)
    mask = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    empresa = Empresa.objects.get(cnpj=mask)
    assert empresa.usuario == nucleado_user
    assert empresa.organizacao == nucleado_user.organizacao


@pytest.mark.django_db
def test_duplicate_cnpj_returns_error(client, nucleado_user):
    client.force_login(nucleado_user)
    cnpj = CNPJ().generate()
    mask = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    EmpresaFactory(usuario=nucleado_user, organizacao=nucleado_user.organizacao, cnpj=mask)
    data = {
        "nome": "Outra",
        "cnpj": cnpj,
        "tipo": "mei",
        "municipio": "Cidade",
        "estado": "SP",
        "descricao": "",
        "palavras_chave": "",
        "tags": [],
    }
    resp = client.post(reverse("empresas:empresa_criar"), data)
    assert resp.status_code == 200
    assert "já existe" in resp.content.decode()


@pytest.mark.django_db
def test_soft_delete_marks_deleted(client, nucleado_user):
    empresa = EmpresaFactory(usuario=nucleado_user, organizacao=nucleado_user.organizacao)
    client.force_login(nucleado_user)
    resp = client.post(reverse("empresas:remover", args=[empresa.pk]))
    assert resp.status_code in (302, 200)
    empresa.refresh_from_db()
    assert empresa.deleted
    resp = client.get(reverse("empresas:lista"))
    assert empresa.nome not in resp.content.decode()


@pytest.mark.django_db
def test_avaliacao_unica_e_media(client, nucleado_user, admin_user):
    empresa = EmpresaFactory(usuario=nucleado_user, organizacao=nucleado_user.organizacao)
    client.force_login(nucleado_user)
    url = reverse("empresas:avaliacao_criar", args=[empresa.pk])
    resp = client.post(url, {"nota": 4, "comentario": "ok"})
    assert resp.status_code in (302, 200)
    # segunda tentativa deve redirecionar para edição
    resp = client.post(url, {"nota": 5}, follow=True)
    assert AvaliacaoEmpresa.objects.filter(empresa=empresa, usuario=nucleado_user).count() == 1
    AvaliacaoEmpresa.objects.create(empresa=empresa, usuario=admin_user, nota=2)
    assert empresa.media_avaliacoes() == 3


@pytest.mark.django_db
def test_avaliacao_comentario_hx_request(client, nucleado_user):
    empresa = EmpresaFactory(usuario=nucleado_user, organizacao=nucleado_user.organizacao)
    client.force_login(nucleado_user)
    url = reverse("empresas:avaliacao_criar", args=[empresa.pk])
    resp = client.post(
        url,
        {"nota": 5, "comentario": "Ótimo"},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    avaliacao = AvaliacaoEmpresa.objects.get(empresa=empresa, usuario=nucleado_user)
    assert avaliacao.nota == 5
    assert avaliacao.comentario == "Ótimo"


@pytest.mark.django_db
def test_avaliacao_update_requires_active(client, nucleado_user):
    empresa = EmpresaFactory(usuario=nucleado_user, organizacao=nucleado_user.organizacao)
    AvaliacaoEmpresa.objects.create(
        empresa=empresa, usuario=nucleado_user, nota=5, deleted=True
    )
    client.force_login(nucleado_user)
    url = reverse("empresas:avaliacao_editar", args=[empresa.pk])
    resp = client.get(url)
    assert resp.status_code == 404
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert any("nenhuma avaliação ativa" in m.lower() for m in msgs)


@pytest.mark.django_db
def test_admin_can_list_deleted(client, admin_user):
    emp = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, deleted=True)
    client.force_login(admin_user)
    resp = client.get(reverse("empresas:lista"), {"mostrar_excluidas": "1"})
    assert emp.nome in resp.content.decode()


@pytest.mark.django_db
def test_admin_sees_restore_and_purge_actions(client, admin_user):
    emp = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, deleted=True)
    client.force_login(admin_user)
    resp = client.get(reverse("empresas:lista"), {"mostrar_excluidas": "1"})
    content = resp.content.decode()
    assert "Restaurar" in content
    assert "Purgar" in content


@pytest.mark.django_db
def test_admin_excludes_deleted_by_default(client, admin_user):
    emp = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, deleted=True)
    client.force_login(admin_user)
    resp = client.get(reverse("empresas:lista"))
    assert emp.nome not in resp.content.decode()


@pytest.mark.django_db
def test_historico_view_access(client, admin_user, nucleado_user):
    empresa = EmpresaFactory(usuario=nucleado_user, organizacao=nucleado_user.organizacao)
    EmpresaChangeLog.objects.create(
        empresa=empresa,
        usuario=nucleado_user,
        campo_alterado="nome",
        valor_antigo="X",
        valor_novo="Y",
    )
    url = reverse("empresas:historico", args=[empresa.id])
    client.force_login(nucleado_user)
    resp = client.get(url)
    assert resp.status_code == 403
    client.force_login(admin_user)
    resp = client.get(url)
    assert resp.status_code == 200
    assert "nome" in resp.content.decode()

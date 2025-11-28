import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from validate_docbr import CNPJ

from organizacoes.factories import OrganizacaoFactory

User = get_user_model()


@pytest.fixture(autouse=True)
def _stub_enviar_para_usuario(monkeypatch):
    from notificacoes.services import notificacoes

    monkeypatch.setattr(notificacoes, "enviar_para_usuario", lambda *_, **__: None)


@pytest.mark.django_db
def test_aceitar_conexao_htmx(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(other)

    client.force_login(user)
    url = reverse("conexoes:aceitar_conexao", args=[other.id])
    resp = client.post(url, HTTP_HX_REQUEST="true")
    assert resp.status_code == 204
    assert resp.headers.get("HX-Trigger")
    assert user.connections.filter(id=other.id).exists()
    assert not user.followers.filter(id=other.id).exists()


@pytest.mark.django_db
def test_recusar_conexao_htmx(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(other)

    client.force_login(user)
    url = reverse("conexoes:recusar_conexao", args=[other.id])
    resp = client.post(url, HTTP_HX_REQUEST="true")
    assert resp.status_code == 204
    assert resp.headers.get("HX-Trigger")
    assert not user.connections.filter(id=other.id).exists()
    assert not user.followers.filter(id=other.id).exists()


@pytest.mark.django_db
def test_recusar_conexao_htmx_invalida(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")

    client.force_login(user)
    url = reverse("conexoes:recusar_conexao", args=[other.id])
    resp = client.post(url, HTTP_HX_REQUEST="true")

    assert resp.status_code == 404
    trigger = json.loads(resp.headers.get("HX-Trigger", "{}"))
    assert trigger.get("conexoes:refresh") is True


@pytest.mark.django_db
def test_perfil_conexoes_solicitacoes_page(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    follower = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(follower)

    client.force_login(user)
    url = reverse("conexoes:perfil_sections_conexoes")
    response = client.get(url, {"tab": "solicitacoes"})

    assert response.status_code == 200
    assert any(template.name == "conexoes/solicitacoes.html" for template in response.templates)
    assert list(response.context["connection_requests"]) == [follower]


@pytest.mark.django_db
def test_perfil_conexoes_solicitacoes_partial_htmx(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    follower = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(follower)

    client.force_login(user)
    url = reverse("conexoes:perfil_conexoes_partial")
    response = client.get(url, {"tab": "solicitacoes"}, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    assert any(template.name == "conexoes/partiais/request_list.html" for template in response.templates)
    assert list(response.context["connection_requests"]) == [follower]


@pytest.mark.django_db
def test_buscar_pessoas_lista_membros_da_organizacao(client):
    organizacao = OrganizacaoFactory()
    outra_org = OrganizacaoFactory()
    user = User.objects.create_user(
        email="owner@example.com",
        username="owner",
        password="x",
        organizacao=organizacao,
        is_associado=True,
    )
    membro_a = User.objects.create_user(
        email="a@exemplo.com",
        username="assoc-a",
        password="x",
        organizacao=organizacao,
        is_associado=True,
        contato="Maria",
    )
    User.objects.create_user(
        email="externo@exemplo.com",
        username="externo",
        password="x",
        organizacao=outra_org,
        is_associado=True,
    )

    client.force_login(user)
    url = reverse("conexoes:perfil_conexoes_buscar")
    response = client.get(url, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    membros = list(response.context["membros"])
    assert membro_a in membros
    assert user not in membros


@pytest.mark.django_db
def test_buscar_pessoas_filtra_por_nome_razao_social_e_cnpj(client):
    organizacao = OrganizacaoFactory()
    user = User.objects.create_user(
        email="owner@example.com",
        username="owner",
        password="x",
        organizacao=organizacao,
        is_associado=True,
    )

    cnpj_generator = CNPJ()
    cnpj_valido = cnpj_generator.generate(mask=True)

    membro_nome = User.objects.create_user(
        email="nome@example.com",
        username="assoc-nome",
        password="x",
        organizacao=organizacao,
        is_associado=True,
        contato="Ana Silva",
    )
    membro_razao = User.objects.create_user(
        email="razao@example.com",
        username="assoc-razao",
        password="x",
        organizacao=organizacao,
        is_associado=True,
        razao_social="Empresa Exemplo Ltda",
    )
    membro_cnpj = User.objects.create_user(
        email="cnpj@example.com",
        username="assoc-cnpj",
        password="x",
        organizacao=organizacao,
        is_associado=True,
        cnpj=cnpj_valido,
    )

    client.force_login(user)
    url = reverse("conexoes:perfil_conexoes_buscar")

    resp_nome = client.get(url, {"q": "Ana"}, HTTP_HX_REQUEST="true")
    assert list(resp_nome.context["membros"]) == [membro_nome]

    resp_razao = client.get(url, {"q": "Empresa Exemplo"}, HTTP_HX_REQUEST="true")
    assert list(resp_razao.context["membros"]) == [membro_razao]

    resp_cnpj = client.get(url, {"q": cnpj_valido.replace(".", "").replace("/", "").replace("-", "")}, HTTP_HX_REQUEST="true")
    assert list(resp_cnpj.context["membros"]) == [membro_cnpj]


@pytest.mark.django_db
def test_solicitar_conexao_cria_solicitacao(client):
    organizacao = OrganizacaoFactory()
    user = User.objects.create_user(
        email="owner@example.com",
        username="owner",
        password="x",
        organizacao=organizacao,
        is_associado=True,
    )
    outro = User.objects.create_user(
        email="outro@example.com",
        username="outro",
        password="x",
        organizacao=organizacao,
        is_associado=True,
    )

    client.force_login(user)
    url = reverse("conexoes:solicitar_conexao", args=[outro.id])
    response = client.post(url, {"q": ""}, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    assert outro.followers.filter(id=user.id).exists()


@pytest.mark.django_db
def test_solicitar_conexao_aceita_pedido_cruzado(client):
    organizacao = OrganizacaoFactory()
    primeiro = User.objects.create_user(
        email="owner@example.com",
        username="owner",
        password="x",
        organizacao=organizacao,
        is_associado=True,
    )
    segundo = User.objects.create_user(
        email="segundo@example.com",
        username="segundo",
        password="x",
        organizacao=organizacao,
        is_associado=True,
    )

    client.force_login(primeiro)
    response_primeiro = client.post(
        reverse("conexoes:solicitar_conexao", args=[segundo.id]),
        {"q": ""},
        HTTP_HX_REQUEST="true",
    )

    assert response_primeiro.status_code == 200
    assert segundo.followers.filter(id=primeiro.id).exists()

    client.force_login(segundo)
    response_segundo = client.post(
        reverse("conexoes:solicitar_conexao", args=[primeiro.id]),
        {"q": ""},
        HTTP_HX_REQUEST="true",
    )

    assert response_segundo.status_code == 200
    assert segundo.connections.filter(id=primeiro.id).exists()
    assert primeiro.connections.filter(id=segundo.id).exists()
    assert not segundo.followers.filter(id=primeiro.id).exists()
    assert not primeiro.followers.filter(id=segundo.id).exists()


@pytest.mark.django_db
def test_remover_conexao_htmx_retorna_template(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.connections.add(other)

    client.force_login(user)
    url = reverse("conexoes:remover_conexao", args=[other.id])
    response = client.post(
        url,
        {"q": ""},
        HTTP_HX_REQUEST="true",
        HTTP_HX_TARGET="perfil-content",
    )

    assert response.status_code == 200
    assert not user.connections.filter(id=other.id).exists()

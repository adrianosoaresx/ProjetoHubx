import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from validate_docbr import CNPJ

from organizacoes.factories import OrganizacaoFactory

User = get_user_model()


@pytest.mark.django_db
def test_aceitar_conexao(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(other)

    client.force_login(user)
    url = reverse("accounts:aceitar_conexao", args=[other.id])
    resp = client.post(url)
    assert resp.status_code == 302
    assert user.connections.filter(id=other.id).exists()
    assert not user.followers.filter(id=other.id).exists()


@pytest.mark.django_db
def test_recusar_conexao(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(other)

    client.force_login(user)
    url = reverse("accounts:recusar_conexao", args=[other.id])
    resp = client.post(url)
    assert resp.status_code == 302
    assert not user.connections.filter(id=other.id).exists()
    assert not user.followers.filter(id=other.id).exists()


@pytest.mark.django_db
def test_buscar_pessoas_lista_associados_da_organizacao(client):
    organizacao = OrganizacaoFactory()
    outra_org = OrganizacaoFactory()
    user = User.objects.create_user(
        email="owner@example.com",
        username="owner",
        password="x",
        organizacao=organizacao,
        is_associado=True,
    )
    associado_a = User.objects.create_user(
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
    url = reverse("accounts:perfil_conexoes_buscar")
    response = client.get(url, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    associados = list(response.context["associados"])
    assert associado_a in associados
    assert user not in associados


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

    associado_nome = User.objects.create_user(
        email="nome@example.com",
        username="assoc-nome",
        password="x",
        organizacao=organizacao,
        is_associado=True,
        contato="Ana Silva",
    )
    associado_razao = User.objects.create_user(
        email="razao@example.com",
        username="assoc-razao",
        password="x",
        organizacao=organizacao,
        is_associado=True,
        razao_social="Empresa Exemplo Ltda",
    )
    associado_cnpj = User.objects.create_user(
        email="cnpj@example.com",
        username="assoc-cnpj",
        password="x",
        organizacao=organizacao,
        is_associado=True,
        cnpj=cnpj_valido,
    )

    client.force_login(user)
    url = reverse("accounts:perfil_conexoes_buscar")

    resp_nome = client.get(url, {"q": "Ana"}, HTTP_HX_REQUEST="true")
    assert list(resp_nome.context["associados"]) == [associado_nome]

    resp_razao = client.get(url, {"q": "Empresa Exemplo"}, HTTP_HX_REQUEST="true")
    assert list(resp_razao.context["associados"]) == [associado_razao]

    resp_cnpj = client.get(url, {"q": cnpj_valido.replace(".", "").replace("/", "").replace("-", "")}, HTTP_HX_REQUEST="true")
    assert list(resp_cnpj.context["associados"]) == [associado_cnpj]

import pytest
from django.urls import reverse

from accounts.models import UserType
from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from empresas.factories import EmpresaFactory
from empresas.models import ContatoEmpresa


@pytest.mark.django_db
def test_contatos_visiveis_para_usuario_autorizado(client):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN.value, organizacao=org, nucleo_obj=None)
    empresa = EmpresaFactory(usuario=user, organizacao=org)
    contato = ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="Fulano",
        cargo="Dev",
        email="f@example.com",
        telefone="123",
    )

    client.force_login(user)
    resp = client.get(reverse("empresas:detail", args=[empresa.pk]))
    content = resp.content.decode()
    assert contato.nome in content
    assert reverse("empresas:contato_editar", args=[contato.id]) in content
    assert reverse("empresas:contato_remover", args=[contato.id]) in content
    assert reverse("empresas:contato_novo", args=[empresa.id]) in content


@pytest.mark.django_db
def test_contatos_invisiveis_para_usuario_nao_autorizado(client):
    org = OrganizacaoFactory()
    owner = UserFactory(user_type=UserType.NUCLEADO.value, organizacao=org, nucleo_obj=None)
    empresa = EmpresaFactory(usuario=owner, organizacao=org)
    contato = ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="Fulano",
        cargo="Dev",
        email="f@example.com",
        telefone="123",
    )
    other = UserFactory(user_type=UserType.NUCLEADO.value, organizacao=org, nucleo_obj=None)

    client.force_login(other)
    resp = client.get(reverse("empresas:detail", args=[empresa.pk]))
    content = resp.content.decode()
    assert contato.nome not in content
    # tentativa de editar deve ser proibida
    edit_url = reverse("empresas:contato_editar", args=[contato.id])
    assert client.get(edit_url).status_code == 403

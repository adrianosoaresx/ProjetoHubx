import pytest

from empresas.factories import EmpresaFactory
from accounts.factories import UserFactory
from empresas.models import AvaliacaoEmpresa
from empresas.tasks import (
    criar_post_avaliacao,
    criar_post_empresa,
    validar_cnpj_empresa,
)
from feed.models import Post


@pytest.mark.django_db
def test_validar_cnpj_atualiza_campos(monkeypatch):
    monkeypatch.setattr("empresas.signals.criar_post_empresa.delay", lambda *a, **k: None)
    monkeypatch.setattr("empresas.signals.validar_cnpj_empresa.delay", lambda *a, **k: None)
    empresa = EmpresaFactory(validado_em=None, fonte_validacao="")

    def fake_validator(cnpj):
        return True, "teste"

    monkeypatch.setattr("empresas.tasks.validar_cnpj", fake_validator)
    validar_cnpj_empresa(str(empresa.id))
    empresa.refresh_from_db()
    assert empresa.fonte_validacao == "teste"
    assert empresa.validado_em is not None


@pytest.mark.django_db
def test_criar_post_empresa(monkeypatch):
    monkeypatch.setattr("empresas.signals.criar_post_empresa.delay", lambda *a, **k: None)
    monkeypatch.setattr("empresas.signals.validar_cnpj_empresa.delay", lambda *a, **k: None)
    empresa = EmpresaFactory()
    criar_post_empresa(str(empresa.id))
    assert Post.objects.filter(conteudo__icontains=empresa.nome).exists()


@pytest.mark.django_db
def test_criar_post_avaliacao_apenas_nota_alta(monkeypatch):
    monkeypatch.setattr("empresas.signals.criar_post_empresa.delay", lambda *a, **k: None)
    monkeypatch.setattr("empresas.signals.validar_cnpj_empresa.delay", lambda *a, **k: None)
    empresa = EmpresaFactory()
    aval = AvaliacaoEmpresa.objects.create(empresa=empresa, usuario=empresa.usuario, nota=5)
    criar_post_avaliacao(str(aval.id))
    assert Post.objects.filter(conteudo__icontains=empresa.nome).count() == 1

    outro_usuario = UserFactory(organizacao=empresa.organizacao)
    aval2 = AvaliacaoEmpresa.objects.create(empresa=empresa, usuario=outro_usuario, nota=2)
    criar_post_avaliacao(str(aval2.id))
    assert Post.objects.filter(conteudo__icontains=empresa.nome).count() == 1

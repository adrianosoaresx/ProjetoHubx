import logging

import pytest

from accounts.models import UserType
from nucleos.models import Nucleo, ParticipacaoNucleo
from nucleos.tasks import notify_participacao_aprovada, notify_participacao_recusada
from organizacoes.models import Organizacao


pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")


@pytest.fixture
def usuario(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="user",
        email="user@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


@pytest.fixture
def nucleo(organizacao):
    return Nucleo.objects.create(nome="N1", organizacao=organizacao)


@pytest.mark.parametrize("task", [notify_participacao_aprovada, notify_participacao_recusada])
def test_notify_participacao_tasks_soft_deleted(task, monkeypatch, nucleo, usuario):
    part = ParticipacaoNucleo.objects.create(user=usuario, nucleo=nucleo, status="ativo")
    part.delete()
    called = []

    def fake_enviar(*args, **kwargs):
        called.append(True)

    monkeypatch.setattr("nucleos.tasks.enviar_para_usuario", fake_enviar)
    task(part.id)
    assert called


@pytest.mark.parametrize("task", [notify_participacao_aprovada, notify_participacao_recusada])
def test_notify_participacao_tasks_missing(task, monkeypatch, caplog):
    called = []

    def fake_enviar(*args, **kwargs):
        called.append(True)

    monkeypatch.setattr("nucleos.tasks.enviar_para_usuario", fake_enviar)
    with caplog.at_level(logging.WARNING):
        task(999999)
    assert "participacao_nucleo_not_found" in caplog.text
    assert not called


def test_limpar_contadores_convites_without_delete_pattern(monkeypatch):
    cache.clear()
    cache.set("convites_nucleo:1", "a")
    cache.set("convites_nucleo:2", "b")
    cache.set("other", "c")

    # Simula backend sem suporte a delete_pattern
    monkeypatch.delattr(cache, "delete_pattern", raising=False)

    limpar_contadores_convites()

    assert cache.get("convites_nucleo:1") is None
    assert cache.get("convites_nucleo:2") is None
    assert cache.get("other") == "c"

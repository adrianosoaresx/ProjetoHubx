import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from nucleos.tasks import notify_suplente_designado


@pytest.mark.django_db
def test_notify_suplente_designado_envia_somente_para_suplente(monkeypatch):
    nucleo = NucleoFactory()
    User = get_user_model()
    suplente = User.objects.create_user(
        username="suplente",
        email="suplente@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=nucleo.organizacao,
    )
    outro = User.objects.create_user(
        username="outro",
        email="outro@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=nucleo.organizacao,
    )
    ParticipacaoNucleo.objects.create(user=suplente, nucleo=nucleo, status="ativo")
    ParticipacaoNucleo.objects.create(user=outro, nucleo=nucleo, status="ativo")

    enviados = []

    def fake_enviar_para_usuario(user, template, context):
        enviados.append(user.email)

    monkeypatch.setattr("nucleos.tasks.enviar_para_usuario", fake_enviar_para_usuario)

    notify_suplente_designado(nucleo.id, suplente.email)

    assert enviados == [suplente.email]


@pytest.mark.django_db
def test_notify_suplente_designado_sem_duplicidades_com_varias_participacoes(monkeypatch):
    nucleo = NucleoFactory()
    outro_nucleo = NucleoFactory(organizacao=nucleo.organizacao)
    User = get_user_model()
    suplente = User.objects.create_user(
        username="suplente",
        email="suplente@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=nucleo.organizacao,
    )
    ParticipacaoNucleo.objects.create(user=suplente, nucleo=nucleo, status="ativo")
    ParticipacaoNucleo.objects.create(user=suplente, nucleo=outro_nucleo, status="ativo")

    enviados: list[str] = []

    def fake_enviar_para_usuario(user, template, context):
        enviados.append(user.email)

    monkeypatch.setattr("nucleos.tasks.enviar_para_usuario", fake_enviar_para_usuario)

    notify_suplente_designado(nucleo.id, suplente.email)

    assert enviados == [suplente.email]

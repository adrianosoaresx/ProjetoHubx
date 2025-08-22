import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from unittest.mock import patch

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00000000000191")


@pytest.fixture
def gerente(client, organizacao):
    user = User.objects.create_user(
        username="gerente",
        email="gerente@example.com",
        password="123",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )
    client.force_login(user)
    return user


@pytest.fixture
def usuario_comum(client, organizacao):
    user = User.objects.create_user(username="c", email="c@x.com", password="123", organizacao=organizacao)
    client.force_login(user)
    return user


@pytest.fixture
def evento(organizacao, gerente):
    return Evento.objects.create(
        titulo="E",
        descricao="d",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="x",
        cidade="y",
        estado="SP",
        cep="00000-000",
        coordenador=gerente,
        organizacao=organizacao,
        status=0,
        publico_alvo=0,
        numero_convidados=10,
        numero_presentes=0,
    )

pytestmark = pytest.mark.django_db


def test_lista_espera(client, usuario_comum, gerente, evento):
    evento.participantes_maximo = 1
    evento.espera_habilitada = True
    evento.save()
    client.force_login(gerente)
    client.post(reverse("agenda:evento_subscribe", args=[evento.pk]))
    client.force_login(usuario_comum)
    client.post(reverse("agenda:evento_subscribe", args=[evento.pk]))
    ins2 = InscricaoEvento.objects.get(user=usuario_comum, evento=evento)
    assert ins2.status == "pendente" and ins2.posicao_espera == 1
    InscricaoEvento.objects.filter(user=gerente, evento=evento).delete()
    from agenda.tasks import promover_lista_espera

    promover_lista_espera(evento.pk)
    ins2.refresh_from_db()
    assert ins2.status == "confirmada"


def test_promover_lista_espera_enqueued_on_cancel(gerente, evento):
    ins = InscricaoEvento.objects.create(
        user=gerente,
        evento=evento,
        status="confirmada",
        data_confirmacao=timezone.now(),
    )
    with patch("agenda.tasks.promover_lista_espera.delay") as delay:
        ins.cancelar_inscricao()
    delay.assert_called_once_with(str(evento.pk))


def test_promover_lista_espera_enqueued_on_delete(gerente, evento):
    ins = InscricaoEvento.objects.create(
        user=gerente,
        evento=evento,
        status="confirmada",
        data_confirmacao=timezone.now(),
    )
    with patch("agenda.tasks.promover_lista_espera.delay") as delay:
        ins.delete()
    delay.assert_called_once_with(str(evento.pk))


def test_promover_lista_espera_enqueued_on_increase(evento):
    evento.participantes_maximo = 1
    evento.save()
    with patch("agenda.tasks.promover_lista_espera.delay") as delay:
        evento.participantes_maximo = 2
        evento.save()
    delay.assert_called_once_with(str(evento.pk))

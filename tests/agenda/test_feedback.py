import pytest
from django.urls import reverse
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from agenda.models import Evento
from accounts.models import User
from organizacoes.models import Organizacao
from freezegun import freeze_time

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")


@pytest.fixture
def evento_passado(organizacao):
    return Evento.objects.create(
        organizacao=organizacao,
        titulo="Evento Antigo",
        descricao="Já aconteceu",
        data_hora=make_aware(datetime(2024, 6, 10, 14, 0)),
        duracao=timedelta(hours=2),
        briefing="",
    )


@pytest.fixture
def usuario(client):
    user = User.objects.create_user(
        username="pessoa", email="pessoa@example.com", password="12345", tipo_id=User.Tipo.PADRAO
    )
    client.force_login(user)
    return user


@freeze_time("2025-07-14 10:00:00")
def test_envio_feedback_pos_evento(evento_passado, usuario, client):
    evento_passado.inscritos.add(usuario)
    evento_passado.save()

    url = reverse("agenda:evento_feedback", args=[evento_passado.pk])
    data = {"nota": "5"}

    response = client.post(url, data=data)
    assert response.status_code in [200, 302]

    evento_passado.refresh_from_db()
    # Aqui depende do modelo: adaptável
    assert evento_passado.feedbacknota_set.filter(usuario=usuario, nota=5).exists()

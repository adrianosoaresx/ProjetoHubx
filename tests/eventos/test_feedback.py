from datetime import datetime

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware
from freezegun import freeze_time

from accounts.models import User, UserType
from eventos.models import Evento, FeedbackNota, InscricaoEvento
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")


@pytest.fixture
def evento_passado(organizacao, usuario):
    return Evento.objects.create(
        organizacao=organizacao,
        titulo="Evento Antigo",
        descricao="Já aconteceu",
        data_inicio=make_aware(datetime(2024, 6, 10, 14, 0)),
        data_fim=make_aware(datetime(2024, 6, 10, 16, 0)),
        coordenador=usuario,
        status=Evento.Status.ATIVO,  # Ativo
        publico_alvo=1,  # Corrigido para usar um número inteiro válido
        numero_convidados=50,  # Adicionado para corrigir o erro
        numero_presentes=30,  # Adicionado para corrigir o erro
    )


@pytest.fixture
def usuario(client, organizacao):
    user = User.objects.create_user(
        username="cliente",
        email="cliente@example.com",
        password="12345",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    client.force_login(user)
    return user


@pytest.fixture
def feedbacks(evento_passado, usuario):
    outro_usuario = User.objects.create_user(
        username="outro_pessoa",
        email="outro_pessoa@example.com",
        password="12345",
        user_type=UserType(usuario.user_type),
    )
    FeedbackNota.objects.create(evento=evento_passado, usuario=usuario, nota=4)
    FeedbackNota.objects.create(
        evento=evento_passado, usuario=outro_usuario, nota=5
    )  # Usar outro usuário para evitar duplicação


@freeze_time("2025-07-14 10:00:00")
def test_envio_feedback_pos_evento(evento_passado, usuario, client):
    InscricaoEvento.objects.create(
        evento=evento_passado,
        user=usuario,
        data_confirmacao=make_aware(datetime.now()),
        status="confirmada",
        presente=False,
    )  # Corrigido argumento 'data_confirmacao'

    url = reverse("eventos:evento_feedback", args=[evento_passado.pk])
    data = {"nota": "5"}

    response = client.post(url, data=data)
    assert response.status_code in [200, 302]

    evento_passado.refresh_from_db()
    assert evento_passado.feedbacks.filter(usuario=usuario, nota=5).exists()


def test_calcular_media_feedback(evento_passado, feedbacks):
    media = evento_passado.calcular_media_feedback()
    assert media == 4.5

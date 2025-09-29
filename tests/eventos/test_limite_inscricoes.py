from datetime import datetime, timedelta

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils.timezone import make_aware

from accounts.models import User, UserType
from eventos.models import Evento, InscricaoEvento
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
    user = User.objects.create_user(
        username="participante",
        email="participante@example.com",
        password="123",
        organizacao=organizacao,
    )
    client.force_login(user)
    return user


@pytest.fixture
def evento(organizacao, gerente):
    return Evento.objects.create(
        titulo="Evento",
        descricao="Descrição",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Auditório",
        cidade="Cidade",
        estado="SP",
        cep="00000-000",
        coordenador=gerente,
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_convidados=10,
        numero_presentes=0,
        participantes_maximo=1,
    )


pytestmark = pytest.mark.django_db


def test_nao_permite_inscricao_quando_evento_lotado(client, gerente, usuario_comum, evento):
    client.force_login(gerente)
    client.post(reverse("eventos:evento_subscribe", args=[evento.pk]))

    client.force_login(usuario_comum)
    resp = client.post(reverse("eventos:evento_subscribe", args=[evento.pk]))

    assert resp.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_comum).exists()

    messages = list(get_messages(resp.wsgi_request))
    assert any("Evento lotado" in str(message) for message in messages)


def test_confirmar_inscricao_lotada_dispara_erro(evento, gerente, usuario_comum):
    primeira = InscricaoEvento.objects.create(user=gerente, evento=evento)
    primeira.confirmar_inscricao()

    segunda = InscricaoEvento.objects.create(user=usuario_comum, evento=evento)

    with pytest.raises(ValueError, match="Evento lotado"):
        segunda.confirmar_inscricao()

    segunda.refresh_from_db()
    assert segunda.status == "pendente"

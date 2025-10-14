from datetime import datetime, timedelta

import pytest
from django.utils.timezone import make_aware

from accounts.models import User, UserType
from eventos.models import Evento
from eventos.querysets import filter_eventos_por_usuario
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao


@pytest.mark.django_db
def test_admin_with_nucleo_membership_sees_all_org_events():
    organizacao = Organizacao.objects.create(
        nome="Org",
        cnpj="00000000000191",
        descricao="Org Teste",
        slug="org",
    )
    nucleo = Nucleo.objects.create(organizacao=organizacao, nome="Núcleo A")
    outro_nucleo = Nucleo.objects.create(organizacao=organizacao, nome="Núcleo B")

    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="123456",
        organizacao=organizacao,
        user_type=UserType.ADMIN,
    )
    ParticipacaoNucleo.objects.create(
        user=admin,
        nucleo=nucleo,
        status="ativo",
        papel="membro",
    )

    base_kwargs = {
        "descricao": "Evento",
        "data_inicio": make_aware(datetime.now() + timedelta(days=1)),
        "data_fim": make_aware(datetime.now() + timedelta(days=2)),
        "local": "Rua 1",
        "cidade": "Cidade",
        "estado": "SC",
        "cep": "12345-678",
        "organizacao": organizacao,
        "status": Evento.Status.ATIVO,
        "numero_convidados": 10,
    }

    evento_publico = Evento.objects.create(
        titulo="Público",
        publico_alvo=0,
        **base_kwargs,
    )
    evento_restrito = Evento.objects.create(
        titulo="Restrito",
        publico_alvo=1,
        nucleo=outro_nucleo,
        **base_kwargs,
    )

    resultados = filter_eventos_por_usuario(Evento.objects.all(), admin)

    assert {evento_publico, evento_restrito} == set(resultados)


import threading
from datetime import datetime, timedelta

import pytest
from django.utils.timezone import make_aware

from accounts.models import User, UserType
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao
from django.db import connection, OperationalError


pytestmark = pytest.mark.django_db(transaction=True)


def test_waitlist_position_unique_concurrent(django_db_blocker):
    org = Organizacao.objects.create(nome="Org", cnpj="00000000000191")
    user1 = User.objects.create_user(
        username="u1",
        email="u1@example.com",
        password="123",
        user_type=UserType.COORDENADOR,
        organizacao=org,
    )
    user2 = User.objects.create_user(username="u2", email="u2@example.com", password="123", organizacao=org)
    user3 = User.objects.create_user(username="u3", email="u3@example.com", password="123", organizacao=org)

    event = Evento.objects.create(
        titulo="E",
        descricao="d",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="x",
        cidade="y",
        estado="SP",
        cep="00000-000",
        coordenador=user1,
        organizacao=org,
        status=0,
        publico_alvo=0,
        numero_convidados=10,
        numero_presentes=0,
        participantes_maximo=1,
        espera_habilitada=True,
    )

    ins1 = InscricaoEvento.objects.create(user=user1, evento=event)
    ins1.confirmar_inscricao()

    ins2 = InscricaoEvento.objects.create(user=user2, evento=event)
    ins3 = InscricaoEvento.objects.create(user=user3, evento=event)

    barrier = threading.Barrier(2)
    connection.cursor().execute("PRAGMA busy_timeout = 5000")

    def worker(pk):
        with django_db_blocker.unblock():
            ins = InscricaoEvento.objects.get(pk=pk)
            barrier.wait()
            for _ in range(5):
                try:
                    ins.confirmar_inscricao()
                    break
                except OperationalError:
                    import time

                    time.sleep(0.1)

    t1 = threading.Thread(target=worker, args=(ins2.pk,))
    t2 = threading.Thread(target=worker, args=(ins3.pk,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    ins2.refresh_from_db()
    ins3.refresh_from_db()

    assert {ins2.posicao_espera, ins3.posicao_espera} == {1, 2}
    assert ins2.status == ins3.status == "pendente"

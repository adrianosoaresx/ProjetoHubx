import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import connection, IntegrityError
from django.db.migrations.executor import MigrationExecutor

from accounts.models import User
from organizacoes.models import Organizacao
from agenda.models import Evento


@pytest.mark.django_db(transaction=True)
def test_migracao_avaliacao_limpa_valores_invalidos():
    user = User.objects.create(username="u", email="u@example.com")
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0000-00", slug="org")
    evento = Evento.objects.create(
        titulo="Ev",
        descricao="Desc",
        data_inicio=timezone.now(),
        data_fim=timezone.now() + timedelta(hours=1),
        local="Loc",
        cidade="Cidade",
        estado="ST",
        cep="00000-000",
        status=0,
        publico_alvo=0,
        numero_convidados=10,
        numero_presentes=5,
        valor_ingresso=Decimal("1.00"),
        orcamento=Decimal("2.00"),
        cronograma="",
        informacoes_adicionais="",
        contato_nome="Nome",
        contato_email="contato@example.com",
        contato_whatsapp="123",
        coordenador=user,
        organizacao=org,
    )

    executor = MigrationExecutor(connection)
    executor.migrate([
        ("agenda", "0003_alter_eventolog_options_alter_tarefalog_options_and_more"),
    ])
    apps = executor.loader.project_state([
        ("agenda", "0003_alter_eventolog_options_alter_tarefalog_options_and_more"),
    ]).apps
    InscricaoEventoOld = apps.get_model("agenda", "InscricaoEvento")
    inscricao = InscricaoEventoOld.objects.create(
        user_id=user.id,
        evento_id=evento.id,
        avaliacao=0,
    )

    executor.loader.build_graph()
    executor.migrate([
        ("agenda", "0004_inscricao_avaliacao_constraint"),
    ])
    InscricaoEventoNew = executor.loader.project_state([
        ("agenda", "0004_inscricao_avaliacao_constraint"),
    ]).apps.get_model("agenda", "InscricaoEvento")
    inscricao_refreshed = InscricaoEventoNew.objects.get(pk=inscricao.pk)
    assert inscricao_refreshed.avaliacao is None

    with pytest.raises(IntegrityError):
        InscricaoEventoNew.objects.create(
            user_id=user.id,
            evento_id=evento.id,
            avaliacao=6,
        )

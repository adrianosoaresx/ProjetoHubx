from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from accounts.models import UserType
from dashboard import services
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao


@pytest.mark.django_db
def test_calculate_monthly_membros_returns_expected_totals(django_user_model):
    reference = timezone.make_aware(datetime(2024, 6, 1, 12, 0, 0))
    organizacao = Organizacao.objects.create(
        nome="Org",
        cnpj="12.345.678/0001-90",
    )

    def create_membro(email: str, joined: datetime) -> None:
        django_user_model.objects.create_user(
            email=email,
            username=email.split("@")[0],
            password="password",
            organizacao=organizacao,
            is_associado=True,
            user_type=UserType.ASSOCIADO,
            date_joined=timezone.make_aware(joined),
        )

    create_membro("abril@example.com", datetime(2024, 4, 10, 9, 0, 0))
    create_membro("maio-a@example.com", datetime(2024, 5, 5, 8, 0, 0))
    create_membro("maio-b@example.com", datetime(2024, 5, 5, 16, 0, 0))
    create_membro("maio-c@example.com", datetime(2024, 5, 12, 11, 30, 0))

    resultado = services.calculate_monthly_membros(
        organizacao, months=3, reference=reference
    )

    assert [registro["period"].month for registro in resultado] == [4, 5, 6]
    assert [registro["total"] for registro in resultado] == [1, 3, 0]
    assert resultado[1]["std_dev"] == pytest.approx(0.5)


@pytest.mark.django_db
def test_calculate_monthly_registration_values_includes_std_dev(django_user_model):
    reference = timezone.make_aware(datetime(2024, 6, 1, 12, 0, 0))
    organizacao = Organizacao.objects.create(
        nome="Org",
        cnpj="98.765.432/0001-10",
    )

    evento = Evento.objects.create(
        titulo="Workshop",
        slug="workshop-dashboard",
        descricao="Evento para testar métricas",
        data_inicio=timezone.make_aware(datetime(2024, 5, 1, 9, 0, 0)),
        data_fim=timezone.make_aware(datetime(2024, 5, 1, 12, 0, 0)),
        local="Auditório",
        cidade="Florianopolis",
        estado="SC",
        cep="88000-000",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        gratuito=False,
        valor_associado=Decimal("100.00"),
        valor_nucleado=Decimal("80.00"),
    )

    def criar_participante(alias: str):
        return django_user_model.objects.create_user(
            email=f"participante-{alias}@example.com",
            username=f"participante-{alias}",
            password="password",
            organizacao=organizacao,
            is_associado=True,
            user_type=UserType.ASSOCIADO,
        )

    def confirmar_inscricao(valor: str, data: datetime, alias: str) -> None:
        InscricaoEvento.objects.create(
            user=criar_participante(alias),
            evento=evento,
            status="confirmada",
            valor_pago=Decimal(valor),
            data_confirmacao=timezone.make_aware(data),
        )

    confirmar_inscricao("80.00", datetime(2024, 4, 25, 10, 0, 0), "abril")
    confirmar_inscricao("100.00", datetime(2024, 5, 10, 10, 0, 0), "maio1")
    confirmar_inscricao("140.00", datetime(2024, 5, 12, 15, 30, 0), "maio2")
    confirmar_inscricao("160.00", datetime(2024, 5, 20, 9, 15, 0), "maio3")

    InscricaoEvento.objects.create(  # Não deve ser considerado
        user=criar_participante("cancelada"),
        evento=evento,
        status="cancelada",
        valor_pago=Decimal("999.99"),
        data_confirmacao=timezone.make_aware(datetime(2024, 5, 22, 9, 0, 0)),
    )

    valores = services.calculate_monthly_registration_values(
        organizacao, months=3, reference=reference
    )
    contagens = services.calculate_monthly_event_registrations(
        organizacao, months=3, reference=reference
    )

    assert [registro["period"].month for registro in valores] == [4, 5, 6]
    assert [round(registro["total"], 2) for registro in valores] == [80.0, 400.0, 0.0]
    assert valores[1]["std_dev"] == pytest.approx(24.94, rel=1e-2)
    assert [registro["total"] for registro in contagens] == [1, 3, 0]

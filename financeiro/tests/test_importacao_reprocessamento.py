import csv
import uuid
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroTaskLog,
    LancamentoFinanceiro,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


def auth(client, user):
    user.user_type = UserType.ADMIN
    user.save()
    client.force_authenticate(user=user)


def make_csv(rows: list[list[str]]) -> bytes:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "centro_custo_id",
            "conta_associado_id",
            "tipo",
            "valor",
            "data_lancamento",
            "data_vencimento",
            "status",
        ]
    )
    writer.writerows(rows)
    return buf.getvalue().encode()


def test_reprocessamento_nao_duplica_lancamentos(api_client, user, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    data = timezone.now().isoformat()

    rows = [
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "10",
            data,
            "",
            "pago",
        ],
        [
            str(centro.id),
            str(uuid.uuid4()),
            "aporte_interno",
            "20",
            data,
            "",
            "pago",
        ],
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 201
    token = resp.data["id"]
    importacao_id = resp.data["importacao_id"]
    token_erros = resp.data["token_erros"]

    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    assert LancamentoFinanceiro.objects.count() == 1

    err_url = reverse("financeiro_api:financeiro-reprocessar-erros", args=[token_erros])
    corrected = make_csv(
        [
            [
                str(centro.id),
                str(conta.id),
                "aporte_interno",
                "10",
                data,
                "",
                "pago",
            ],
            [
                str(centro.id),
                str(conta.id),
                "aporte_interno",
                "20",
                data,
                "",
                "pago",
            ],
        ]
    )
    file2 = SimpleUploadedFile("corr.csv", corrected, content_type="text/csv")
    resp = api_client.post(err_url, {"file": file2}, format="multipart")
    assert resp.status_code == 202
    log = FinanceiroTaskLog.objects.filter(nome_tarefa="reprocessar_importacao_async").first()
    assert log is not None
    assert log.status == "erro"
    assert "duplicado" in log.detalhes.lower()
    assert LancamentoFinanceiro.objects.count() == 2

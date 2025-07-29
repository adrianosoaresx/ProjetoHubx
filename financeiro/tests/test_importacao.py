import csv
from io import BytesIO, StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
import uuid

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


def auth(client, user):
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


def test_invalid_extension(api_client, user):
    auth(api_client, user)
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    file = SimpleUploadedFile("data.txt", b"x")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 400


def test_missing_columns(api_client, user):
    auth(api_client, user)
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    buf = BytesIO(b"a,b\n1,2")
    file = SimpleUploadedFile("data.csv", buf.getvalue(), content_type="text/csv")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 400


def test_preview_and_confirm(api_client, user, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    rows = [
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "10",
            timezone.now().isoformat(),
            timezone.now().isoformat(),
            "pago",
        ],
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "20",
            timezone.now().isoformat(),
            timezone.now().isoformat(),
            "pago",
        ],
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 201
    token = resp.data["id"]
    assert len(resp.data["preview"]) == 2

    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    resp = api_client.post(confirm_url, {"id": token})
    assert resp.status_code == 202
    assert LancamentoFinanceiro.objects.count() == 2
    centro.refresh_from_db()
    assert centro.saldo == 30


def test_invalid_vencimento(api_client, user):
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    rows = [
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "10",
            timezone.now().isoformat(),
            (timezone.now() - timezone.timedelta(days=1)).isoformat(),
            "pago",
        ]
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 400

def test_reprocessar_erros(api_client, user, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    rows = [
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "10",
            timezone.now().isoformat(),
            "",  # missing vencimento -> ok
            "pago",
        ],
        [  # linha inválida (conta inexistente)
            str(centro.id),
            str(uuid.uuid4()),
            "aporte_interno",
            "20",
            timezone.now().isoformat(),
            timezone.now().isoformat(),
            "pago",
        ],
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 201
    token = resp.data["token_erros"]
    err_url = reverse("financeiro_api:financeiro-reprocessar-erros", args=[token])
    # corrige arquivo apenas com linha válida
    corrected = make_csv([
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "20",
            timezone.now().isoformat(),
            timezone.now().isoformat(),
            "pago",
        ]
    ])
    file2 = SimpleUploadedFile("corr.csv", corrected, content_type="text/csv")
    resp = api_client.post(err_url, {"file": file2}, format="multipart")
    assert resp.status_code == 200
    assert LancamentoFinanceiro.objects.count() == 2

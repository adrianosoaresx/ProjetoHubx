import csv
from io import StringIO

import pytest
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, ContaAssociado, ImportacaoPagamentos


pytestmark = pytest.mark.django_db


def make_csv(rows):
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "centro_custo_id",
        "conta_associado_id",
        "tipo",
        "valor",
        "data_lancamento",
        "data_vencimento",
        "status",
    ])
    writer.writerows(rows)
    return buf.getvalue().encode()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


def test_fluxo_importacao_listagem(api_client, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=user)
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
        ]
    ]
    file = SimpleUploadedFile("data.csv", make_csv(rows), content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    importacao_id = resp.data["importacao_id"]
    token = resp.data["id"]
    assert ImportacaoPagamentos.objects.filter(id=importacao_id).exists()

    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    imp = ImportacaoPagamentos.objects.get(id=importacao_id)
    assert imp.total_processado == 1

    list_url = reverse("financeiro_api:importacao-list")
    resp = api_client.get(list_url, {"usuario": str(user.id), "periodo_inicial": timezone.now().strftime("%Y-%m")})
    assert resp.status_code == 200
    assert resp.data["count"] >= 1
    detail_url = reverse("financeiro_api:importacao-detail", args=[importacao_id])
    resp = api_client.get(detail_url)
    assert resp.status_code == 200
    assert resp.data["id"] == str(importacao_id)


def test_rejects_large_file(api_client):
    user = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=user)
    big_content = b"0" * (5 * 1024 * 1024 + 1)
    file = SimpleUploadedFile("data.csv", big_content, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 400
    assert "file" in resp.data

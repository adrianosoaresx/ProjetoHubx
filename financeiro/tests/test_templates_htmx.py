import csv
import re
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, ContaAssociado


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    user = UserFactory()
    user.user_type = UserType.ADMIN
    user.save()
    return user


@pytest.fixture
def client_logged(client, admin_user):
    client.force_login(admin_user)
    return client


def test_importar_pagamentos_template_structure(client_logged):
    resp = client_logged.get(reverse("financeiro:importar_pagamentos"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'id="file"' in html
    match = re.search(r'<button[^>]*id="confirm-btn"[^>]*>', html)
    assert match and "disabled" in match.group(0)


def _make_csv(rows: list[list[str]]) -> bytes:
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


@pytest.fixture
def api_client(admin_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


def test_fluxo_importacao_htmx(api_client, settings, admin_user):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=admin_user)
    now = timezone.now().isoformat()
    rows = [[str(centro.id), str(conta.id), "aporte_interno", "10", now, now, "pago"]]
    file = SimpleUploadedFile("data.csv", _make_csv(rows), content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart", HTTP_HX_REQUEST="true")
    assert resp.status_code == 201
    token = resp.data["id"]
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    resp2 = api_client.post(confirm_url, {"id": token}, HTTP_HX_REQUEST="true")
    assert resp2.status_code == 202


def test_importar_pagamentos_template_sanitizes_errors(client_logged):
    resp = client_logged.get(reverse("financeiro:importar_pagamentos"))
    html = resp.content.decode()
    assert "document.createElement('li')" in html
    assert "li.textContent = err" in html
    assert "<li>${e}</li>" not in html

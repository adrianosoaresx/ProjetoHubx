import csv
import uuid
from decimal import Decimal
from io import BytesIO, StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import (
    Carteira,
    CentroCusto,
    ContaAssociado,
    FinanceiroTaskLog,
    ImportacaoPagamentos,
    LancamentoFinanceiro,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _override_urls(settings):
    settings.ROOT_URLCONF = "tests.financeiro_api_urls"


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
    carteira_centro = Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
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
    importacao_id = resp.data["importacao_id"]
    assert len(resp.data["preview"]) == 2

    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    resp = api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    assert resp.status_code == 202
    assert LancamentoFinanceiro.objects.count() == 2
    centro.refresh_from_db()
    conta.refresh_from_db()
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert carteira_centro.saldo == Decimal("30")
    assert carteira_conta.saldo == Decimal("30")
    assert centro.saldo == 0
    assert conta.saldo == 0
    assert LancamentoFinanceiro.objects.filter(origem=LancamentoFinanceiro.Origem.IMPORTACAO).count() == 2
    importacao = ImportacaoPagamentos.objects.get(pk=importacao_id)
    assert importacao.status == ImportacaoPagamentos.Status.CONCLUIDO


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
    token = resp.data["id"]
    importacao_id = resp.data["importacao_id"]
    token_erros = resp.data["token_erros"]
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    err_url = reverse("financeiro_api:financeiro-reprocessar-erros", args=[token_erros])
    # corrige arquivo apenas com linha válida
    corrected = make_csv(
        [
            [
                str(centro.id),
                str(conta.id),
                "aporte_interno",
                "20",
                timezone.now().isoformat(),
                timezone.now().isoformat(),
                "pago",
            ]
        ]
    )
    file2 = SimpleUploadedFile("corr.csv", corrected, content_type="text/csv")
    resp = api_client.post(err_url, {"file": file2}, format="multipart")
    assert resp.status_code == 202
    assert LancamentoFinanceiro.objects.count() == 2
    log = FinanceiroTaskLog.objects.filter(nome_tarefa="reprocessar_importacao_async").first()
    assert log is not None
    assert log.status == "sucesso"


def test_email_nao_cadastrado(api_client, user):
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "centro_custo_id",
            "email",
            "tipo",
            "valor",
            "data_lancamento",
            "data_vencimento",
            "status",
        ]
    )
    writer.writerow(
        [
            str(centro.id),
            "naoexiste@example.com",
            "aporte_interno",
            "10",
            timezone.now().isoformat(),
            "",
            "pago",
        ]
    )
    csv_bytes = buf.getvalue().encode()
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 400
    assert "e-mail" in " ".join(resp.data.get("erros", [])).lower()


def test_metrics_increment(api_client, user, settings):
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
        ]
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    token = resp.data["id"]
    importacao_id = resp.data["importacao_id"]
    from financeiro.services import metrics

    before = metrics.importacao_pagamentos_total._value.get()
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    assert metrics.importacao_pagamentos_total._value.get() == before + 1


def test_confirm_twice_idempotent(api_client, user, settings):
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
        ]
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    token = resp.data["id"]
    importacao_id = resp.data["importacao_id"]
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    assert LancamentoFinanceiro.objects.count() == 1
    importacao = ImportacaoPagamentos.objects.get(pk=importacao_id)
    assert importacao.total_processado == 1
    assert importacao.status == ImportacaoPagamentos.Status.CONCLUIDO


def test_ignore_duplicate_lines(api_client, user, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    row = [
        str(centro.id),
        str(conta.id),
        "aporte_interno",
        "10",
        timezone.now().isoformat(),
        timezone.now().isoformat(),
        "pago",
    ]
    csv_bytes = make_csv([row, row])
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    token = resp.data["id"]
    importacao_id = resp.data["importacao_id"]
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    assert LancamentoFinanceiro.objects.count() == 1
    log = ImportacaoPagamentos.objects.latest("data_importacao")
    assert log.total_processado == 1
    assert log.erros


def test_ignore_existing_entries(api_client, user, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    data_lanc = timezone.now()
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo="aporte_interno",
        valor=Decimal("10"),
        data_lancamento=data_lanc,
        data_vencimento=data_lanc,
        status=LancamentoFinanceiro.Status.PAGO,
    )
    row = [
        str(centro.id),
        str(conta.id),
        "aporte_interno",
        "10",
        data_lanc.isoformat(),
        data_lanc.isoformat(),
        "pago",
    ]
    csv_bytes = make_csv([row])
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    token = resp.data["id"]
    importacao_id = resp.data["importacao_id"]
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    assert LancamentoFinanceiro.objects.count() == 1
    log = ImportacaoPagamentos.objects.latest("data_importacao")
    assert log.total_processado == 0
    assert log.erros


def test_negative_value_invalid(api_client, user):
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    rows = [
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "-10",
            timezone.now().isoformat(),
            timezone.now().isoformat(),
            "pago",
        ]
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 400


def test_negative_value_despesa_valid(api_client, user, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=user)
    rows = [
        [
            str(centro.id),
            str(conta.id),
            "despesa",
            "-15",
            timezone.now().isoformat(),
            timezone.now().isoformat(),
            "pago",
        ]
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 201
    token = resp.data["id"]
    importacao_id = resp.data["importacao_id"]
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    resp = api_client.post(confirm_url, {"id": token, "importacao_id": importacao_id})
    assert resp.status_code == 202
    lanc = LancamentoFinanceiro.objects.get()
    assert lanc.tipo == "despesa"
    assert lanc.valor == Decimal("-15")

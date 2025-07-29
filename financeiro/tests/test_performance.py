import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from organizacoes.factories import OrganizacaoFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
import uuid

from .test_importacao import make_csv

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_relatorios_query_count(api_client, django_assert_num_queries):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org)
    centro = CentroCusto.objects.create(nome="C1", tipo="organizacao", organizacao=org)
    ContaAssociado.objects.create(user=user)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=10,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        status=LancamentoFinanceiro.Status.PAGO,
    )
    api_client.force_authenticate(user=user)
    url = reverse("financeiro_api:financeiro-relatorios") + f"?centro={centro.id}"
    with django_assert_num_queries(5):
        resp = api_client.get(url)
    assert resp.status_code == 200


def test_importacao_benchmark(api_client, settings, benchmark):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    admin = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=admin)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    conta = ContaAssociado.objects.create(user=admin)
    rows = [
        [
            str(centro.id),
            str(conta.id),
            "aporte_interno",
            "1",
            timezone.now().isoformat(),
            timezone.now().isoformat(),
            "pago",
        ]
        for _ in range(1000)
    ]
    csv_bytes = make_csv(rows)
    file = SimpleUploadedFile("data.csv", csv_bytes, content_type="text/csv")
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    resp = api_client.post(url, {"file": file}, format="multipart")
    token = resp.data["id"]
    confirm_url = reverse("financeiro_api:financeiro-confirmar-importacao")
    benchmark(lambda: api_client.post(confirm_url, {"id": token}))

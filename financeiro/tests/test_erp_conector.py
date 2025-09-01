import pytest
from unittest.mock import Mock, patch
from requests import Timeout

from financeiro.models import IntegracaoConfig, IntegracaoLog
from financeiro.services.integracoes.erp_conector import ERPConector
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_request_retries_and_logs_success_after_failure():
    org = OrganizacaoFactory()
    config = IntegracaoConfig.objects.create(
        organizacao=org,
        nome="ERP Teste",
        tipo=IntegracaoConfig.Tipo.ERP,
        base_url="https://example.com",
    )
    conector = ERPConector(config, retries=2, backoff=0)

    success_response = Mock(status_code=200, ok=True, text="")
    success_response.json.return_value = {"ok": True}
    success_response.raise_for_status = Mock()

    with patch.object(
        conector.session,
        "request",
        side_effect=[Timeout("timeout"), success_response],
    ):
        response = conector._request("GET", "/teste/", json={})

    assert response.json() == {"ok": True}

    logs = list(IntegracaoLog.objects.filter(provedor=config.nome).order_by("created_at"))
    assert len(logs) == 2
    assert logs[0].status == "timeout"
    assert "tentativa 1" in logs[0].acao
    assert logs[1].status == "200"
    assert "tentativa 2" in logs[1].acao

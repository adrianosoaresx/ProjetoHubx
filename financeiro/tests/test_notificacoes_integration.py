import pytest
from types import SimpleNamespace
from django.utils import timezone
from unittest.mock import MagicMock

from accounts.factories import UserFactory
from financeiro.models import LancamentoFinanceiro
from financeiro.services.notificacoes import enviar_cobranca

pytestmark = pytest.mark.django_db


def test_enviar_cobranca_templates(monkeypatch):
    user = UserFactory()
    lanc = SimpleNamespace(
        valor=10,
        data_vencimento=timezone.now(),
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
    )
    mocked = MagicMock()
    monkeypatch.setattr("financeiro.services.notificacoes.enviar_para_usuario", mocked)
    enviar_cobranca(user, lanc)
    assert mocked.call_count == 1
    assert mocked.call_args.args[1] == "mensalidade_associacao"
    mocked.reset_mock()
    lanc.tipo = LancamentoFinanceiro.Tipo.MENSALIDADE_NUCLEO
    enviar_cobranca(user, lanc)
    assert mocked.call_count == 1
    assert mocked.call_args.args[1] == "mensalidade_nucleo"

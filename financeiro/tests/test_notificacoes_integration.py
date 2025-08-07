import pytest
from types import SimpleNamespace
from django.utils import timezone
from unittest.mock import MagicMock

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.serializers import AporteSerializer
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


def test_aporte_serializer_envia_notificacao(monkeypatch):
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    user = UserFactory()
    conta = ContaAssociado.objects.create(user=user)
    data = {
        "centro_custo": str(centro.id),
        "conta_associado": str(conta.id),
        "valor": "10",
        "tipo": LancamentoFinanceiro.Tipo.APORTE_INTERNO,
    }
    mocked = MagicMock()
    monkeypatch.setattr("financeiro.serializers.enviar_aporte", mocked)
    serializer = AporteSerializer(data=data, context={"request": SimpleNamespace(user=user)})
    assert serializer.is_valid(), serializer.errors
    lanc = serializer.save()
    mocked.assert_called_once_with(user, lanc)

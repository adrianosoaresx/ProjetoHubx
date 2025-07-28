import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.serializers import LancamentoFinanceiroSerializer
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_lancamento_atualiza_saldos():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Org", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=org)
    user = UserFactory()
    conta = ContaAssociado.objects.create(user=user)
    serializer = LancamentoFinanceiroSerializer(
        data={
            "centro_custo": str(centro.id),
            "conta_associado": str(conta.id),
            "tipo": LancamentoFinanceiro.Tipo.APORTE_INTERNO,
            "valor": "100",
            "data_lancamento": timezone.now(),
            "status": LancamentoFinanceiro.Status.PAGO,
            "descricao": "teste",
        }
    )
    assert serializer.is_valid(), serializer.errors
    lanc = serializer.save()
    centro.refresh_from_db()
    conta.refresh_from_db()
    assert centro.saldo == lanc.valor
    assert conta.saldo == lanc.valor

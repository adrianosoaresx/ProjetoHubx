import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro


pytestmark = pytest.mark.django_db


def test_associado_pode_acessar_extrato(client):
    user = UserFactory(user_type=UserType.ASSOCIADO)
    conta = ContaAssociado.objects.create(user=user)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao")
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=100,
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    client.force_login(user)
    resp = client.get(reverse("financeiro:extrato"))
    assert resp.status_code == 200
    assert len(resp.context["lancamentos"]) == 1


def test_nao_associado_sem_acesso(client):
    user = UserFactory(user_type=UserType.ADMIN)
    client.force_login(user)
    resp = client.get(reverse("financeiro:extrato"))
    assert resp.status_code == 403

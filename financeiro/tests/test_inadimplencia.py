from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroTaskLog,
    LancamentoFinanceiro,
)
from financeiro.tasks.inadimplencia import notificar_inadimplencia
from financeiro.viewsets import FinanceiroViewSet
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_notificacao_task_respeita_intervalo(monkeypatch, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    enviar = MagicMock()
    monkeypatch.setattr("financeiro.tasks.inadimplencia.enviar_inadimplencia", enviar)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    user = UserFactory(user_type=UserType.ADMIN)
    conta = ContaAssociado.objects.create(user=user)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now() - timezone.timedelta(days=10),
        data_vencimento=timezone.now() - timezone.timedelta(days=5),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now() - timezone.timedelta(days=10),
        data_vencimento=timezone.now() - timezone.timedelta(days=5),
        status=LancamentoFinanceiro.Status.PENDENTE,
        ultima_notificacao=timezone.now() - timezone.timedelta(days=2),
    )
    notificar_inadimplencia.delay()
    assert enviar.call_count == 1
    assert FinanceiroTaskLog.objects.filter(nome_tarefa="notificar_inadimplencia").exists()


def test_notificacao_aviso_vencimento(monkeypatch, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    aviso = MagicMock()
    inadimplencia = MagicMock()
    monkeypatch.setattr("financeiro.tasks.inadimplencia.enviar_aviso_vencimento", aviso)
    monkeypatch.setattr("financeiro.tasks.inadimplencia.enviar_inadimplencia", inadimplencia)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    user = UserFactory(user_type=UserType.ADMIN)
    conta = ContaAssociado.objects.create(user=user)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        data_vencimento=timezone.now() + timezone.timedelta(days=2),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    notificar_inadimplencia.delay()
    assert aviso.call_count == 1
    assert inadimplencia.call_count == 0
    assert FinanceiroTaskLog.objects.filter(nome_tarefa="notificar_inadimplencia").exists()


def test_inadimplencias_endpoint(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory(user_type=UserType.ADMIN)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    conta = ContaAssociado.objects.create(user=user)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        data_vencimento=timezone.now() - timezone.timedelta(days=3),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    factory = APIRequestFactory()
    request = factory.get("/api/financeiro/inadimplencias/")
    force_authenticate(request, user=user)
    view = FinanceiroViewSet.as_view({"get": "inadimplencias"})
    resp = view(request)
    assert resp.status_code == 200
    assert resp.data[0]["dias_atraso"] >= 3

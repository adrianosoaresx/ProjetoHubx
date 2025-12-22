import os
from datetime import timedelta
from decimal import Decimal

import django
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from eventos.models import Evento, InscricaoEvento  # noqa: E402
from organizacoes.models import Organizacao  # noqa: E402
from pagamentos.models import Transacao  # noqa: E402
from pagamentos.services.pagamento import PagamentoService  # noqa: E402


@pytest.mark.django_db
def test_pix_checkout_success(monkeypatch) -> None:
    User = get_user_model()
    user = User.objects.create_user(username="cliente", password="senha123", email="c@example.com")
    organizacao = Organizacao.objects.create(nome="Org", cnpj="12345678000195")
    evento = Evento.objects.create(
        titulo="Evento Pix",
        slug="evento-pix",
        descricao="Descricao",
        data_inicio=timezone.now() + timedelta(days=2),
        data_fim=timezone.now() + timedelta(days=3),
        local="Local",
        cidade="Cidade",
        estado="SP",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        gratuito=False,
        valor_associado=Decimal("150.00"),
        valor_nucleado=Decimal("150.00"),
    )
    inscricao = InscricaoEvento.objects.create(user=user, evento=evento)

    def fake_iniciar_pagamento(self, pedido, metodo, dados_pagamento):
        return Transacao.objects.create(
            pedido=pedido,
            valor=pedido.valor,
            status=Transacao.Status.APROVADA,
            metodo=Transacao.Metodo.PIX,
            detalhes={"status": "approved"},
        )

    monkeypatch.setattr(PagamentoService, "iniciar_pagamento", fake_iniciar_pagamento)

    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("pagamentos:pix-checkout"),
        data={
            "valor": "150.00",
            "metodo": Transacao.Metodo.PIX,
            "email": "cliente@example.com",
            "nome": "Cliente Teste",
            "documento": "12345678909",
            "pix_expiracao": (timezone.now() + timedelta(days=1)).isoformat(),
            "inscricao_uuid": str(inscricao.uuid),
        },
    )

    assert response.status_code == 302
    transacao = Transacao.objects.order_by("-pk").first()
    assert transacao is not None
    assert reverse("pagamentos:checkout-resultado", kwargs={"pk": transacao.pk}) in response["Location"]

    inscricao.refresh_from_db()
    assert inscricao.metodo_pagamento == Transacao.Metodo.PIX
    assert inscricao.pagamento_validado is True


@pytest.mark.django_db
def test_faturamento_checkout_updates_inscricao() -> None:
    User = get_user_model()
    user = User.objects.create_user(username="financeiro", password="senha123", email="f@example.com")
    organizacao = Organizacao.objects.create(nome="Org", cnpj="12345678000196")
    evento = Evento.objects.create(
        titulo="Evento Faturamento",
        slug="evento-faturamento",
        descricao="Descricao",
        data_inicio=timezone.now() + timedelta(days=2),
        data_fim=timezone.now() + timedelta(days=3),
        local="Local",
        cidade="Cidade",
        estado="SP",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        gratuito=False,
        valor_associado=Decimal("200.00"),
        valor_nucleado=Decimal("200.00"),
    )
    inscricao = InscricaoEvento.objects.create(user=user, evento=evento)

    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("pagamentos:faturamento-checkout"),
        data={
            "valor": "200.00",
            "condicao_faturamento": "2x",
            "inscricao_uuid": str(inscricao.uuid),
        },
    )

    assert response.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.metodo_pagamento == "faturamento"
    assert inscricao.condicao_faturamento == "2x"
    assert inscricao.valor_pago is None
    assert inscricao.pagamento_validado is False

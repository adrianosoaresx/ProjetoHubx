import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from notificacoes.models import Canal, Frequencia, HistoricoNotificacao

pytestmark = pytest.mark.django_db


def test_historico_only_user(client):
    user1 = UserFactory()
    user2 = UserFactory()
    HistoricoNotificacao.objects.create(
        user=user1,
        canal=Canal.EMAIL,
        frequencia=Frequencia.DIARIA,
        data_referencia=timezone.localdate(),
        conteudo=["m1"],
    )
    HistoricoNotificacao.objects.create(
        user=user2,
        canal=Canal.EMAIL,
        frequencia=Frequencia.DIARIA,
        data_referencia=timezone.localdate(),
        conteudo=["m2"],
    )
    client.force_login(user1)
    resp = client.get(reverse("notificacoes:historico"))
    content = resp.content.decode()
    assert "m1" in content
    assert "m2" not in content


def test_historico_paginacao_filtro(client):
    user = UserFactory()
    for i in range(60):
        ref_date = timezone.now() + timezone.timedelta(days=i)
        HistoricoNotificacao.objects.create(
            user=user,
            canal=Canal.EMAIL if i % 2 == 0 else Canal.WHATSAPP,
            frequencia=Frequencia.DIARIA,
            data_referencia=ref_date.date(),
            conteudo=[f"m{i}"],
            enviado_em=ref_date,
        )
    client.force_login(user)
    resp = client.get(reverse("notificacoes:historico"), {"page": 2, "canal": "whatsapp"})
    assert resp.status_code == 200
    page_obj = resp.context["historicos"]
    assert page_obj.number == 2
    assert all(h.canal == Canal.WHATSAPP for h in page_obj)

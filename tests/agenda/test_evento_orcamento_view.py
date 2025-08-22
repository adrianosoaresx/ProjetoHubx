import pytest
from decimal import Decimal
from django.urls import include, path
from django.test import override_settings

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from agenda.factories import EventoFactory
from agenda.models import EventoLog


pytestmark = pytest.mark.django_db

urlpatterns = [
    path("agenda/", include(("agenda.urls", "agenda"), namespace="agenda")),
]


def _admin_user():
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    return user


@override_settings(ROOT_URLCONF=__name__)
def test_evento_orcamento_atualiza_e_registra_log(client):
    user = _admin_user()
    evento = EventoFactory(
        organizacao=user.organizacao,
        coordenador=user,
        orcamento_estimado=Decimal("100.00"),
        valor_gasto=Decimal("50.00"),
    )
    client.force_login(user)
    url = f"/agenda/api/eventos/{evento.pk}/orcamento/"
    resp = client.post(url, {"orcamento_estimado": "150.50", "valor_gasto": "80.25"})
    assert resp.status_code == 200
    evento.refresh_from_db()
    assert evento.orcamento_estimado == Decimal("150.50")
    assert evento.valor_gasto == Decimal("80.25")
    log = EventoLog.objects.get(evento=evento, acao="orcamento_atualizado")
    assert log.usuario == user
    assert log.detalhes["orcamento_estimado"] == {"antes": "100.00", "depois": "150.50"}
    assert log.detalhes["valor_gasto"] == {"antes": "50.00", "depois": "80.25"}


@override_settings(ROOT_URLCONF=__name__)
def test_evento_orcamento_valores_invalidos(client):
    user = _admin_user()
    evento = EventoFactory(organizacao=user.organizacao, coordenador=user)
    client.force_login(user)
    url = f"/agenda/api/eventos/{evento.pk}/orcamento/"
    resp = client.post(url, {"orcamento_estimado": "abc", "valor_gasto": "10"})
    assert resp.status_code == 400
    assert "errors" in resp.json()
    assert EventoLog.objects.filter(evento=evento, acao="orcamento_atualizado").count() == 0


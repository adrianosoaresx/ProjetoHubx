import pytest
from django.urls import reverse
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory
from eventos.factories import EventoFactory


@pytest.mark.django_db
def test_cliente_cannot_access_other_organizacao(client, cliente_user):
    other_org = OrganizacaoFactory()
    client.force_login(cliente_user)
    url = reverse("dashboard:cliente")
    resp = client.get(url, {"organizacao_id": other_org.id})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_cliente_cannot_access_unauthorized_nucleo(client, cliente_user):
    other_nucleo = NucleoFactory(organizacao=cliente_user.organizacao)
    client.force_login(cliente_user)
    url = reverse("dashboard:cliente")
    resp = client.get(url, {"nucleo_id": other_nucleo.id})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_cliente_cannot_access_unauthorized_evento(client, cliente_user, admin_user):
    other_nucleo = NucleoFactory(organizacao=cliente_user.organizacao)
    evento = EventoFactory(
        organizacao=cliente_user.organizacao, nucleo=other_nucleo, coordenador=admin_user
    )
    client.force_login(cliente_user)
    url = reverse("dashboard:cliente")
    resp = client.get(url, {"evento_id": evento.id})
    assert resp.status_code == 403

import pytest
from django.urls import reverse
from accounts.factories import UserFactory
from eventos.factories import EventoFactory
from empresas.factories import EmpresaFactory
from eventos.models import ParceriaEvento
from accounts.models import UserType
from datetime import date


@pytest.mark.django_db
def test_parceria_list_requires_admin(client):
    evento = EventoFactory()
    user = UserFactory(user_type=UserType.ASSOCIADO, organizacao=evento.organizacao, nucleo_obj=None)
    client.force_login(user)
    resp = client.get(reverse("eventos:parceria_list"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_parceria_list_template(client):
    evento = EventoFactory()
    empresa = EmpresaFactory(organizacao=evento.organizacao)
    ParceriaEvento.objects.create(
        evento=evento,
        empresa=empresa,
        nucleo=evento.nucleo,
        cnpj="12345678901234",
        contato="Contato",
        representante_legal="Rep",
        data_inicio=date.today(),
        data_fim=date.today(),
    )
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento.organizacao, nucleo_obj=None)
    client.force_login(user)
    resp = client.get(reverse("eventos:parceria_list"))
    assert resp.status_code == 200
    assert "agenda/parceria_list.html" in [t.name for t in resp.templates]


@pytest.mark.django_db
def test_parceria_create_evento_outra_org_mostra_erro(client):
    evento_own = EventoFactory()
    evento_other = EventoFactory()
    empresa = EmpresaFactory(organizacao=evento_own.organizacao)
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento_own.organizacao, nucleo_obj=None)
    client.force_login(user)
    data = {
        "evento": evento_other.pk,
        "empresa": empresa.pk,
        "cnpj": "12345678901234",
        "contato": "Contato",
        "representante_legal": "Rep",
        "data_inicio": date.today(),
        "data_fim": date.today(),
        "descricao": "",
    }
    resp = client.post(reverse("eventos:parceria_criar"), data)
    assert resp.status_code == 200
    assert "Evento de outra organização" in resp.content.decode()

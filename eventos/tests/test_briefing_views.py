import pytest
from django.test import override_settings
from django.urls import reverse
from django.contrib.messages import get_messages
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from eventos.factories import EventoFactory
from eventos.models import BriefingEvento
from accounts.models import UserType


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="Hubx.urls")
def test_briefing_create_exibe_mensagem(client):
    evento = EventoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento.organizacao, nucleo_obj=None)
    client.force_login(user)
    data = {
        "evento": evento.pk,
        "objetivos": "obj",
        "publico_alvo": "pub",
        "requisitos_tecnicos": "req",
    }
    resp = client.post(reverse("eventos:briefing_criar"), data, follow=True)
    assert resp.status_code == 200
    template_names = {t.name for t in resp.templates if t.name}
    assert "eventos/painel.html" in template_names or "eventos/partials/briefing/briefing_list.html" in template_names
    messages = list(get_messages(resp.wsgi_request))
    assert any("Briefing criado com sucesso" in m.message for m in messages)


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="Hubx.urls")
def test_briefing_create_duplicate_form_exibe_erro(client):
    evento = EventoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento.organizacao, nucleo_obj=None)
    client.force_login(user)
    data = {
        "evento": evento.pk,
        "objetivos": "obj",
        "publico_alvo": "pub",
        "requisitos_tecnicos": "req",
    }
    primeira_resposta = client.post(reverse("eventos:briefing_criar"), data, follow=True)
    assert primeira_resposta.status_code == 200
    assert BriefingEvento.objects.filter(evento=evento, deleted=False).count() == 1

    resposta = client.post(reverse("eventos:briefing_criar"), data)
    assert resposta.status_code == 200
    form = resposta.context["form"]
    assert "Já existe briefing para este evento." in form.errors.get("evento", [])
    assert BriefingEvento.objects.filter(evento=evento, deleted=False).count() == 1


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="Hubx.urls")
def test_briefing_create_duplicate_api_retorna_erro():
    evento = EventoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento.organizacao, nucleo_obj=None)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("eventos_api:briefing-list")
    payload = {
        "evento": str(evento.pk),
        "objetivos": "obj",
        "publico_alvo": "pub",
        "requisitos_tecnicos": "req",
    }

    primeira_resposta = client.post(url, payload, format="json")
    assert primeira_resposta.status_code == status.HTTP_201_CREATED
    assert BriefingEvento.objects.filter(evento=evento, deleted=False).count() == 1

    resposta = client.post(url, payload, format="json")
    assert resposta.status_code == status.HTTP_400_BAD_REQUEST
    assert resposta.data["evento"][0] == "Já existe briefing ativo para este evento."
    assert BriefingEvento.objects.filter(evento=evento, deleted=False).count() == 1

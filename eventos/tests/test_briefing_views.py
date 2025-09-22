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
    assert "eventos/painel.html" in template_names
    assert "eventos/partials/briefing/briefing_detail.html" in template_names
    messages = list(get_messages(resp.wsgi_request))
    assert any("Briefing criado com sucesso" in m.message for m in messages)


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="Hubx.urls")

def test_briefing_detail_renderiza_e_atualiza(client):
    evento = EventoFactory()
    briefing = BriefingEvento.objects.create(
        evento=evento,
        objetivos="Objetivo inicial",
        publico_alvo="Público",
        requisitos_tecnicos="Requisitos",
        cronograma_resumido="Cronograma",
        conteudo_programatico="Conteúdo",
        observacoes="Observações",
    )
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento.organizacao, nucleo_obj=None)
    client.force_login(user)

    url = reverse("eventos:briefing_detalhe", kwargs={"evento_pk": evento.pk})
    resp = client.get(url)
    assert resp.status_code == 200
    template_names = {t.name for t in resp.templates if t.name}
    assert "eventos/partials/briefing/briefing_detail.html" in template_names
    assert "Prazo limite para resposta" in resp.content.decode()

    data = {
        "objetivos": "Objetivo atualizado",
        "publico_alvo": briefing.publico_alvo,
        "requisitos_tecnicos": briefing.requisitos_tecnicos,
        "cronograma_resumido": briefing.cronograma_resumido,
        "conteudo_programatico": briefing.conteudo_programatico,
        "observacoes": briefing.observacoes,
    }
    resp = client.post(url, data, follow=True)
    assert resp.status_code == 200
    briefing.refresh_from_db()
    assert briefing.objetivos == "Objetivo atualizado"
    messages = list(get_messages(resp.wsgi_request))
    assert any("Briefing atualizado com sucesso" in m.message for m in messages)


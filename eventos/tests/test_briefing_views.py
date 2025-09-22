import pytest
from django.test import override_settings
from django.urls import reverse
from django.contrib.messages import get_messages
from accounts.factories import UserFactory
from eventos.factories import EventoFactory
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
